const BASE = "https://crs-4x319ckwf-like365hondais-projects.vercel.app";

export interface UploadResult {
  job_id: string;
  status: string;
}

export interface JobStatus {
  status: string;
  message: string;
  result_filename: string | null;
}

export async function uploadFiles(
  idmlFile: File,
  wordFile: File
): Promise<UploadResult> {
  const form = new FormData();
  form.append("idml_file", idmlFile);
  form.append("word_file", wordFile);

  const res = await fetch(`${BASE}/api/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error(`Upload failed: ${res.statusText}`);
  }
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/api/status/${jobId}`);
  if (!res.ok) {
    throw new Error(`Status check failed: ${res.statusText}`);
  }
  return res.json();
}

export function getDownloadUrl(jobId: string): string {
  return `${BASE}/api/download/${jobId}`;
}

export function getMappingDownloadUrl(jobId: string): string {
  return `${BASE}/api/download/${jobId}/mapping`;
}
