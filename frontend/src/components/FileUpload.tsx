import { useCallback, useState, useRef } from "react";

interface FileUploadProps {
  label: string;
  badge: string;
  badgeColor: "red" | "blue";
  accept: string;
  fileType: "IDML" | "Word";
  file: File | null;
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

function FileIcon({ type }: { type: "IDML" | "Word" }) {
  if (type === "IDML") {
    return (
      <div className="file-icon idml-icon">
        <svg width="48" height="56" viewBox="0 0 48 56" fill="none">
          <path d="M4 0h28l16 16v36a4 4 0 01-4 4H4a4 4 0 01-4-4V4a4 4 0 014-4z" fill="#8B5CF6" opacity="0.12" />
          <path d="M4 2h26l14 14v36a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2z" stroke="#8B5CF6" strokeWidth="1.5" fill="none" />
          <rect x="8" y="36" width="32" height="12" rx="2" fill="#8B5CF6" />
          <text x="24" y="46" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="700" fontFamily="system-ui">IDML</text>
        </svg>
      </div>
    );
  }
  return (
    <div className="file-icon word-icon">
      <svg width="48" height="56" viewBox="0 0 48 56" fill="none">
        <path d="M4 0h28l16 16v36a4 4 0 01-4 4H4a4 4 0 01-4-4V4a4 4 0 014-4z" fill="#2563EB" opacity="0.12" />
        <path d="M4 2h26l14 14v36a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2z" stroke="#2563EB" strokeWidth="1.5" fill="none" />
        <rect x="8" y="36" width="32" height="12" rx="2" fill="#2563EB" />
        <text x="24" y="46" textAnchor="middle" fill="#fff" fontSize="7" fontWeight="700" fontFamily="system-ui">WORD</text>
      </svg>
    </div>
  );
}

export default function FileUpload({
  label,
  badge,
  badgeColor,
  accept,
  fileType,
  file,
  onFileSelect,
  disabled,
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (f: File) => {
      if (!disabled) onFileSelect(f);
    },
    [onFileSelect, disabled]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleClick = useCallback(() => {
    if (!disabled) inputRef.current?.click();
  }, [disabled]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      className={`file-upload ${isDragOver ? "drag-over" : ""} ${file ? "has-file" : ""} ${disabled ? "disabled" : ""}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleChange}
        hidden
      />

      <span className={`file-badge badge-${badgeColor}`}>{badge}</span>

      <FileIcon type={fileType} />

      <div className="file-upload-label">{label}</div>

      {file ? (
        <div className="file-selected">
          <span className="file-selected-name">{file.name}</span>
          <span className="file-selected-size">{formatSize(file.size)}</span>
        </div>
      ) : (
        <div className="file-upload-hint">
          ドラッグ＆ドロップまたは<span className="hint-link">参照</span>
        </div>
      )}
    </div>
  );
}
