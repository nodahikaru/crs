"""API routes for the mapping pipeline."""

import os
import uuid
import traceback
import time

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from models import UploadResponse, JobStatusResponse
from storage import (
    save_upload, save_result, get_result_path, get_idml_output_path,
    set_job_status, get_job_status,
    upload_files_to_s3,
    upload_mapping_files_to_s3
)
from extractors.idml_extractor import extract_idml_nodes
from extractors.word_extractor import extract_word_nodes
from matcher.embedder import Embedder
from matcher.scorer import compute_mapping
from injector.idml_injector import build_english_idml

from concurrent.futures import ThreadPoolExecutor
router = APIRouter()


def _run_pipeline(job_id: str, idml_path: str, word_path: str) -> None:
    """Background task: run the full matching pipeline + IDML generation."""
    
    start_time = time.perf_counter()
    try:
        # Step A: Extract Japanese text from IDML
        set_job_status(job_id, "processing", "IDMLからテキスト抽出中...")
        ja_nodes = extract_idml_nodes(idml_path)

        # Step B: Extract English text from Word
        set_job_status(job_id, "processing", "Wordからテキスト抽出中...")
        en_nodes = extract_word_nodes(word_path)

        if not ja_nodes:
            set_job_status(job_id, "error", "IDMLファイルからテキストが見つかりませんでした")
            return
        if not en_nodes:
            set_job_status(job_id, "error", "Wordファイルからテキストが見つかりませんでした")
            return

        # Step C: Compute embeddings
        set_job_status(
            job_id, "processing",
            f"Embedding計算中... ({len(ja_nodes)} JA + {len(en_nodes)} EN ノード)"
        )
        
        embedder = Embedder()
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_ja = executor.submit(embedder.embed_batch, [n.text for n in ja_nodes])
            future_en = executor.submit(embedder.embed_batch, [n.text for n in en_nodes])
            
            ja_vecs = future_ja.result()
            en_vecs = future_en.result()

        # Step D: Matching
        set_job_status(job_id, "processing", "マッチング実行中...")
        result = compute_mapping(ja_nodes, en_nodes, ja_vecs, en_vecs)

        # Save mapping JSON
        result_dict = result.to_dict()
        save_result(result_dict, job_id)

        # Step E, F, G: Inject English text into IDML and rebuild
        set_job_status(job_id, "processing", "英語IDML生成中...")
        output_idml_path = get_idml_output_path(job_id)
        build_english_idml(
            source_idml_path=idml_path,
            output_idml_path=output_idml_path,
            mappings=result_dict["mappings"],
        )

        duration = time.perf_counter() - start_time
        duration_str = f"{duration: .2f}s"

        output_filename = os.path.basename(output_idml_path)
        low_conf = result_dict["metrics"]["low_conf_count"]
        total = result_dict["metrics"]["total_mappings"]
        msg = f"完了 — {total}件マッチング (LOW_CONF: {low_conf}件) | 処理時間: {duration_str}"

        set_job_status(job_id, "completed", msg, output_filename)
        upload_files_to_s3(job_id)
        upload_mapping_files_to_s3(job_id)

    except Exception as e:
        traceback.print_exc()
        set_job_status(job_id, "error", str(e))

@router.post("/api/upload", response_model=UploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    idml_file: UploadFile = File(...),
    word_file: UploadFile = File(...),
):
    """Accept IDML + Word files, start matching pipeline in background."""
    job_id = str(uuid.uuid4())[:8]

    # Save uploaded files
    idml_bytes = await idml_file.read()
    word_bytes = await word_file.read()

    idml_path = save_upload(idml_bytes, idml_file.filename or "input.idml", job_id)
    word_path = save_upload(word_bytes, word_file.filename or "input.docx", job_id)

    set_job_status(job_id, "processing", "パイプライン開始...")

    # Run pipeline in background
    background_tasks.add_task(_run_pipeline, job_id, idml_path, word_path)

    return UploadResponse(job_id=job_id, status="processing")


@router.get("/api/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    """Poll job processing status."""
    status = get_job_status(job_id)
    return JobStatusResponse(**status)


@router.get("/api/download/{job_id}")
async def download_idml(job_id: str):
    """Download the generated English IDML file."""
    status = get_job_status(job_id)

    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job status: {status['status']}")

    idml_path = get_idml_output_path(job_id)
    if not os.path.exists(idml_path):
        raise HTTPException(status_code=404, detail="IDML output not found")

    return FileResponse(
        idml_path,
        media_type="application/octet-stream",
        filename=status.get("result_filename", f"{job_id}_output.idml"),
    )


@router.get("/api/download/{job_id}/mapping")
async def download_mapping(job_id: str):
    """Download the mapping JSON result."""
    status = get_job_status(job_id)

    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job status: {status['status']}")

    result_path = get_result_path(job_id)
    if not result_path:
        raise HTTPException(status_code=404, detail="Mapping JSON not found")

    return FileResponse(
        result_path,
        media_type="application/json",
        filename=f"{job_id}_mapping.json",
    )

