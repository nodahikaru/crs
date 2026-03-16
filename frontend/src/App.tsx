import { useState, useCallback, useRef, useEffect } from "react";
import Layout from "./components/Layout";
import FileUpload from "./components/FileUpload";
import ResultPanel from "./components/ResultPanel";
import { uploadFiles, getJobStatus } from "./api";
import "./App.css";

type AppStatus = "idle" | "uploading" | "processing" | "completed" | "error";

function App() {
  const [idmlFile, setIdmlFile] = useState<File | null>(null);
  const [wordFile, setWordFile] = useState<File | null>(null);
  const [status, setStatus] = useState<AppStatus>("idle");
  const [message, setMessage] = useState("");
  const [jobId, setJobId] = useState("");
  const [resultFilename, setResultFilename] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const startPolling = useCallback(
    (jid: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const res = await getJobStatus(jid);
          setMessage(res.message);
          if (res.status === "completed") {
            setStatus("completed");
            setResultFilename(res.result_filename);
            stopPolling();
          } else if (res.status === "error") {
            setStatus("error");
            stopPolling();
          }
        } catch {
          setStatus("error");
          setMessage("サーバーとの接続に失敗しました");
          stopPolling();
        }
      }, 2000);
    },
    [stopPolling]
  );

  const handleExecute = useCallback(async () => {
    if (!idmlFile || !wordFile) return;
    setStatus("uploading");
    setMessage("ファイルをアップロード中...");
    try {
      const result = await uploadFiles(idmlFile, wordFile);
      setJobId(result.job_id);
      setStatus("processing");
      setMessage("処理を開始しています...");
      startPolling(result.job_id);
    } catch (e) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "アップロードに失敗しました");
    }
  }, [idmlFile, wordFile, startPolling]);

  const handleReset = useCallback(() => {
    stopPolling();
    setIdmlFile(null);
    setWordFile(null);
    setStatus("idle");
    setMessage("");
    setJobId("");
    setResultFilename(null);
  }, [stopPolling]);

  const canExecute =
    idmlFile !== null && wordFile !== null && (status === "idle" || status === "completed" || status === "error");
  const isProcessing = status === "uploading" || status === "processing";

  return (
    <Layout>
      <div className="page-container">
        {/* Page header */}
        <div className="page-header">
          <h2 className="page-title">英語版レポートを生成</h2>
          <p className="page-description">
            日本語のレイアウトファイル(IDML)と翻訳原稿(Word)をアップロードして、英語版の統合報告書を自動生成します。
          </p>
        </div>

        {/* Main Card */}
        <div className="main-card">
          {/* Upload Area */}
          <div className="upload-area">
            <FileUpload
              label="日本語 IDMLファイル"
              badge="Source Layout"
              badgeColor="red"
              accept=".idml"
              fileType="IDML"
              file={idmlFile}
              onFileSelect={setIdmlFile}
              disabled={isProcessing}
            />
            <FileUpload
              label="英語 Wordファイル"
              badge="Translation Text"
              badgeColor="blue"
              accept=".docx"
              fileType="Word"
              file={wordFile}
              onFileSelect={setWordFile}
              disabled={isProcessing}
            />
          </div>

          {/* Divider with arrow */}
          <div className="divider">
            <div className="divider-line" />
            <div className="divider-arrow">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 3v12m0 0l-4.5-4.5M10 15l4.5-4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="divider-line" />
          </div>

          {/* Execute */}
          <div className="execute-area">
            <button
              className={`execute-btn ${isProcessing ? "is-loading" : ""} ${canExecute ? "is-ready" : ""}`}
              onClick={handleExecute}
              disabled={!canExecute || isProcessing}
            >
              {isProcessing ? (
                <>
                  <span className="btn-spinner" />
                  <span>処理中...</span>
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="btn-icon">
                    <path d="M9 1.5l2.25 5L16.5 9l-5.25 2.5L9 16.5l-2.25-5L1.5 9l5.25-2.5L9 1.5z" fill="currentColor" />
                  </svg>
                  <span>自動生成を実行</span>
                </>
              )}
            </button>
            <p className="execute-note">※ 生成には数分かかる場合があります</p>
          </div>

          {/* Result */}
          {status !== "idle" && (
            <div className="result-area">
              <ResultPanel
                status={status === "uploading" ? "processing" : status}
                message={message}
                jobId={jobId}
                resultFilename={resultFilename}
                onReset={handleReset}
              />
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default App;
