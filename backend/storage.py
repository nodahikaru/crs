"""Local file storage and in-memory job status management."""

import json
import os
import boto3
import shutil
from config import settings

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION_NAME")
)

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


def upload_files_to_s3(job_id: str):
    local_folder = f"uploads/{job_id}"
    bucket_name = os.getenv("AWS_S3_BUCKET")
    s3_folder = f"{job_id}/"

    # Upload files
    for root, dirs, files in os.walk(local_folder):
        for file in files:
            local_path = os.path.join(root, file)

            relative_path = os.path.relpath(local_path, local_folder)
            s3_key = os.path.join(s3_folder, relative_path).replace("\\", "/")
            s3.upload_file(local_path, bucket_name, s3_key)

def upload_mapping_files_to_s3(job_id: str):
    local_folder = 'outputs'
    bucket_name = os.getenv("AWS_S3_BUCKET")
    s3_folder = f"{job_id}/outputs/"

    files_to_upload = [f"{job_id}_mapping.json", f"{job_id}_output.idml"]

    for file_name in files_to_upload:
        local_path = os.path.join(local_folder, file_name)
        if os.path.exists(local_path):
            s3_key = os.path.join(s3_folder, file_name).replace("\\", "/")
            s3.upload_file(local_path, bucket_name, s3_key)
        else:
            print(f"File not found, skipping: {local_path}")

def delete_local_files():
    try:
        shutil.rmtree("outputs")
        shutil.rmtree("uploads")
    except Exception as e:
        print(f"Error deleting local folder: {e}")
