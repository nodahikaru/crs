interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? "visible" : ""}`}
        onClick={onClose}
      />

      <aside className={`sidebar ${isOpen ? "open" : ""}`}>
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="#6366F1" />
              <path
                d="M8 10h12M8 14h8M8 18h10"
                stroke="#fff"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">Concise IR</span>
            <span className="sidebar-brand-sub">Report System</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <div className="sidebar-section-label">MAIN</div>

          <a className="sidebar-item active" href="#">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M10 2l1.5 3.5L15 7l-3.5 1.5L10 12l-1.5-3.5L5 7l3.5-1.5L10 2z"
                fill="currentColor"
              />
              <path
                d="M4 14l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z"
                fill="currentColor"
                opacity="0.5"
              />
            </svg>
            <span>Generate</span>
          </a>

          <a className="sidebar-item disabled" href="#">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M3 5h14M3 10h14M3 15h14"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            <span>History</span>
            <span className="sidebar-badge">Soon</span>
          </a>

          <div className="sidebar-section-label">SYSTEM</div>

          <a className="sidebar-item disabled" href="#">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle
                cx="10"
                cy="10"
                r="3"
                stroke="currentColor"
                strokeWidth="1.5"
              />
              <path
                d="M10 1.5v2M10 16.5v2M1.5 10h2M16.5 10h2M3.4 3.4l1.4 1.4M15.2 15.2l1.4 1.4M3.4 16.6l1.4-1.4M15.2 4.8l1.4-1.4"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            <span>Settings</span>
            <span className="sidebar-badge">Soon</span>
          </a>

          <a className="sidebar-item disabled" href="#">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <circle
                cx="10"
                cy="10"
                r="8"
                stroke="currentColor"
                strokeWidth="1.5"
              />
              <path
                d="M10 6v4l2.5 2.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>API Usage</span>
            <span className="sidebar-badge">Soon</span>
          </a>
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="sidebar-version">Phase 1 PoC v0.1</div>
        </div>
      </aside>
    </>
  );
}
