interface NavbarProps {
  onMenuToggle: () => void;
}

export default function Navbar({ onMenuToggle }: NavbarProps) {
  return (
    <header className="navbar">
      <div className="navbar-left">
        <button className="navbar-menu-btn" onClick={onMenuToggle}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path
              d="M3 5h14M3 10h14M3 15h14"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </button>
        <div className="navbar-title">
          <h1 className="navbar-heading">Report Generator</h1>
          <span className="navbar-subtitle">
            統合報告書 自動生成
          </span>
        </div>
      </div>

      <div className="navbar-right">
        <div className="navbar-status">
          <span className="status-dot" />
          <span className="status-text">System Ready</span>
        </div>
      </div>
    </header>
  );
}
