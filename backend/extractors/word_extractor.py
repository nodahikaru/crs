"""Extract ordered text nodes from a Word .docx file."""

import re
from dataclasses import dataclass, asdict
from docx import Document


@dataclass
class WordTextNode:
    node_id: str          # e.g. "wp_3"
    paragraph_index: int  # Original paragraph index in document
    text: str             # Full paragraph text (all runs concatenated)
    style: str            # Paragraph style name
    global_order: int     # Sequential order (among non-empty paragraphs)

    def to_dict(self) -> dict:
        return asdict(self)


def split_english_sentences(text: str) -> list[str]:
    """Split English text into sentence-level chunks."""
    if not text:
        return []

    # preserve punctuation; split at . ? ! with optional trailing quote/apos
    parts = re.split(r"(?<=[\.\?!])[\"']?\s+", text)
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def extract_word_nodes(docx_path: str, min_text_length: int = 2) -> list[WordTextNode]:
    """Extract ordered text nodes from a Word document.

    Args:
        docx_path: Path to the .docx file
        min_text_length: Skip nodes shorter than this

    Returns:
        List of WordTextNode ordered by document position
    """
    doc = Document(docx_path)
    nodes: list[WordTextNode] = []
    global_order = 0

    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if len(text) < min_text_length:
            continue

        sentences = split_english_sentences(text)
        for sent_idx, sent_text in enumerate(sentences):
            if len(sent_text) < min_text_length:
                continue

            node = WordTextNode(
                node_id=f"wp_{global_order}",
                paragraph_index=i,
                text=sent_text,
                style=para.style.name,
                global_order=global_order,
            )
            nodes.append(node)
            global_order += 1

    return nodes


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '../doc/英文テキスト.docx'
    nodes = extract_word_nodes(path)
    print(f'Total nodes: {len(nodes)}')
    for n in nodes:
        display = n.text[:80] + '...' if len(n.text) > 80 else n.text
        print(f'[{n.global_order:3d}] {n.node_id:10s} ({n.style}): {display}')
