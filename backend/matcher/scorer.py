"""Score and match Japanese IDML nodes with English Word nodes."""

import time
from dataclasses import dataclass, asdict

import numpy as np

from config import settings
from extractors.idml_extractor import IdmlTextNode
from extractors.word_extractor import WordTextNode


@dataclass
class MappingEntry:
    ja_node_id: str
    en_node_id: str
    ja_text: str
    en_text: str
    score: float
    vector_score: float
    order_score: float
    low_conf: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MappingResult:
    mappings: list[MappingEntry]
    metrics: dict

    def to_dict(self) -> dict:
        return {
            "mappings": [m.to_dict() for m in self.mappings],
            "metrics": self.metrics,
        }


def _cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity matrix between two sets of vectors.

    Args:
        a: (N, dim) array
        b: (M, dim) array

    Returns:
        (N, M) similarity matrix with values in [-1, 1]
    """
    # Normalize rows to unit vectors
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return a_norm @ b_norm.T


def _order_score_matrix(
    ja_nodes: list[IdmlTextNode],
    en_nodes: list[WordTextNode],
    sigma: float | None = None,
) -> np.ndarray:
    """Compute Gaussian-based order score matrix.

    Nodes at similar relative positions get higher scores.
    Uses normalized positions [0, 1] and Gaussian decay.

    Returns:
        (N, M) matrix with values in (0, 1]
    """
    n = len(ja_nodes)
    m = len(en_nodes)

    # Normalize global_order to [0, 1]
    ja_max = max(node.global_order for node in ja_nodes) or 1
    en_max = max(node.global_order for node in en_nodes) or 1

    ja_pos = np.array([node.global_order / ja_max for node in ja_nodes])  # (N,)
    en_pos = np.array([node.global_order / en_max for node in en_nodes])  # (M,)

    # Position difference matrix
    diff = np.abs(ja_pos[:, np.newaxis] - en_pos[np.newaxis, :])  # (N, M)

    # Sigma controls how strict the alignment is
    # Smaller = stricter (only near positions match)
    # Larger = looser (more tolerance)
    if sigma is None:
        sigma = 0.1  # 👈 good default, tune this

    scores = np.exp(-(diff ** 2) / (2 * sigma ** 2))

    return scores


def compute_mapping(
    ja_nodes: list[IdmlTextNode],
    en_nodes: list[WordTextNode],
    ja_embeddings: np.ndarray,
    en_embeddings: np.ndarray,
    top_k: int | None = None,
    vector_weight: float | None = None,
    order_weight: float | None = None,
    low_conf_threshold: float | None = None,
) -> MappingResult:
    """Compute 1-to-1 mapping between Japanese and English text nodes.

    Uses vector similarity + positional order scoring with greedy assignment.

    Args:
        ja_nodes: Japanese text nodes from IDML
        en_nodes: English text nodes from Word
        ja_embeddings: (N, dim) embedding vectors for Japanese nodes
        en_embeddings: (M, dim) embedding vectors for English nodes
        top_k: Number of candidates per Japanese node (default from settings)
        vector_weight: Weight for vector similarity (default from settings)
        order_weight: Weight for order score (default from settings)
        low_conf_threshold: Score threshold for LOW_CONF flag (default from settings)

    Returns:
        MappingResult with mappings and metrics
    """
    start_time = time.time()

    top_k = top_k or settings.TOP_K
    vector_weight = vector_weight if vector_weight is not None else settings.VECTOR_WEIGHT
    order_weight = order_weight if order_weight is not None else settings.ORDER_WEIGHT
    low_conf_threshold = low_conf_threshold if low_conf_threshold is not None else settings.LOW_CONF_THRESHOLD

    n = len(ja_nodes)
    m = len(en_nodes)

    # Step 1: Cosine similarity matrix (N x M)
    sim_matrix = _cosine_similarity_matrix(ja_embeddings, en_embeddings)

    # Step 2: Order score matrix (N x M)
    ord_matrix = _order_score_matrix(ja_nodes, en_nodes)

    # Step 3: Combined score
    total_matrix = vector_weight * sim_matrix + order_weight * ord_matrix

    # Step 4: TopK candidates per Japanese node
    k = min(top_k, m)
    candidates: list[tuple[int, int, float, float, float]] = []  # (ja_idx, en_idx, total, vec, ord)

    for i in range(n):
        top_indices = np.argsort(total_matrix[i])[-k:][::-1]
        for j_idx in top_indices:
            j = int(j_idx)
            candidates.append((
                i, j,
                float(total_matrix[i, j]),
                float(sim_matrix[i, j]),
                float(ord_matrix[i, j]),
            ))

    # Step 5: Greedy 1-to-1 assignment (sort by total score descending)
    candidates.sort(key=lambda x: -x[2])

    assigned_ja: set[int] = set()
    assigned_en: set[int] = set()
    mappings: list[MappingEntry] = []

    for ja_idx, en_idx, total_score, vec_score, ord_score in candidates:
        if ja_idx in assigned_ja or en_idx in assigned_en:
            continue

        assigned_ja.add(ja_idx)
        assigned_en.add(en_idx)
        mappings.append(MappingEntry(
            ja_node_id=ja_nodes[ja_idx].node_id,
            en_node_id=en_nodes[en_idx].node_id,
            ja_text=ja_nodes[ja_idx].text,
            en_text=en_nodes[en_idx].text,
            score=round(total_score, 4),
            vector_score=round(vec_score, 4),
            order_score=round(ord_score, 4),
            low_conf=total_score < low_conf_threshold,
        ))

    # step 6: Add a fallback pass after greedy assignment that assigns remaining unmatched 
    # Japanese nodes to their best still-available English candidate, ignoring top_k
    unmatched_ja = [i for i in range(n) if i not in assigned_ja]
    if unmatched_ja:
        available_mask = np.ones(m, dtype=bool)
        for j in assigned_en:
            available_mask[j] = False
        
        for i in unmatched_ja:
            if not available_mask.any():
                break
            masked = np.where(available_mask, total_matrix[i], -np.inf)
            best_j = int(np.argmax(masked))
            available_mask[best_j] = False
            assigned_en.add(best_j)
            mappings.append(MappingEntry(
                ja_node_id=ja_nodes[i].node_id,
                en_node_id=en_nodes[best_j].node_id,
                ja_text=ja_nodes[i].text,
                en_text=en_nodes[best_j].text,
                score=round(float(total_matrix[i, best_j]), 4),
                vector_score=round(float(sim_matrix[i, best_j]), 4),
                order_score=round(float(ord_matrix[i, best_j]), 4),
                low_conf=True,  # always LOW_CONF since it's a fallback
            ))

    # Sort mappings by Japanese document order
    ja_id_to_order = {n.node_id: n.global_order for n in ja_nodes}
    mappings.sort(key=lambda m: ja_id_to_order.get(m.ja_node_id, 0))

    elapsed = time.time() - start_time
    low_conf_count = sum(1 for m in mappings if m.low_conf)
    avg_score = sum(m.score for m in mappings) / len(mappings) if mappings else 0

    metrics = {
        "total_ja_nodes": n,
        "total_en_nodes": m,
        "total_mappings": len(mappings),
        "low_conf_count": low_conf_count,
        "avg_score": round(avg_score, 4),
        "processing_time_sec": round(elapsed, 2),
    }

    return MappingResult(mappings=mappings, metrics=metrics)
