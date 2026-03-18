"""Local file storage and in-memory job status management."""

import json
import os

from config import settings

# In-memory job status store (single-user local PoC)
_jobs: dict[str, dict] = {}


def save_upload(file_bytes: bytes, filename: str, job_id: str) -> str:
    """Save uploaded file to disk. Returns the file path."""
    job_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    path = os.path.join(job_dir, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path


def save_result(result: dict, job_id: str) -> str:
    """Save mapping JSON result. Returns the file path."""
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(settings.OUTPUT_DIR, f"{job_id}_mapping.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return path


def get_result_path(job_id: str) -> str | None:
    """Get the mapping JSON file path if it exists."""
    path = os.path.join(settings.OUTPUT_DIR, f"{job_id}_mapping.json")
    return path if os.path.exists(path) else None


def get_idml_output_path(job_id: str) -> str:
    """Get the output IDML file path (may not exist yet)."""
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    return os.path.join(settings.OUTPUT_DIR, f"{job_id}_output.idml")


def set_job_status(
    job_id: str,
    status: str,
    message: str = "",
    result_filename: str | None = None,
) -> None:
    _jobs[job_id] = {
        "status": status,
        "message": message,
        "result_filename": result_filename,
    }


def get_job_status(job_id: str) -> dict:
    return _jobs.get(job_id, {
        "status": "not_found",
        "message": "Job not found",
        "result_filename": None,
    })
