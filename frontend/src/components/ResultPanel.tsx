import { getDownloadUrl, getMappingDownloadUrl } from "../api";

interface ResultPanelProps {
  status: string;
  message: string;
  jobId: string;
  resultFilename: string | null;
  onReset: () => void;
}

function ProgressSteps({ message }: { message: string }) {
  const steps = [
    { label: "テキスト抽出", match: "抽出" },
    { label: "Embedding計算", match: "Embedding" },
    { label: "マッチング", match: "マッチング" },
    { label: "IDML生成", match: "IDML" },
  ];

  const currentIdx = steps.findIndex((s) => message.includes(s.match));

  return (
    <div className="progress-steps">
      {steps.map((step, i) => (
        <div
          key={step.label}
          className={`progress-step ${i < currentIdx ? "done" : i === currentIdx ? "active" : ""}`}
        >
          <div className="step-dot">
            {i < currentIdx ? (
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <span>{i + 1}</span>
            )}
          </div>
          <span className="step-label">{step.label}</span>
        </div>
      ))}
    </div>
  );
}

export default function ResultPanel({
  status,
  message,
  jobId,
  resultFilename,
  onReset,
}: ResultPanelProps) {
  if (status === "processing") {
    return (
      <div className="result-panel processing">
        <div className="spinner" />
        <div className="result-status">処理中...</div>
        <div className="result-detail">{message}</div>
        <ProgressSteps message={message} />
      </div>
    );
  }

  if (status === "completed") {
    return (
      <div className="result-panel completed">
        <div className="completed-header">
          <div className="result-check">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="12" fill="#22C55E" />
              <path d="M7 12l3.5 3.5L17 9" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="completed-info">
            <div className="result-status">生成完了</div>
            {resultFilename && (
              <div className="result-filename">{resultFilename}</div>
            )}
            {message && <div className="result-detail success">{message}</div>}
          </div>
        </div>

        <div className="download-buttons">
          <a
            className="download-button primary"
            href={getDownloadUrl(jobId)}
            download={resultFilename || `${jobId}_output.idml`}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="btn-icon">
              <path d="M8 2v8m0 0L5 7m3 3l3-3M3 12h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            IDMLダウンロード
          </a>
          <a
            className="download-button secondary"
            href={getMappingDownloadUrl(jobId)}
            download={`${jobId}_mapping.json`}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="btn-icon">
              <path d="M8 2v8m0 0L5 7m3 3l3-3M3 12h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            マッピングJSON
          </a>
        </div>

        <button className="reset-button" onClick={onReset}>
          新しいファイルで再実行
        </button>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="result-panel error">
        <div className="error-header">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="12" fill="#EF4444" />
            <path d="M12 8v4m0 4h.01" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <div>
            <div className="result-status">エラーが発生しました</div>
            <div className="result-detail error-detail">{message}</div>
          </div>
        </div>
        <button className="reset-button" onClick={onReset}>
          やり直す
        </button>
      </div>
    );
  }

  return null;
}
