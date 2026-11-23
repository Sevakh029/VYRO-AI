function Header({ status }) {
  return (
    <header className="header">
      <div className="brand">
        <p className="brand-mark">VYRO</p>
        <p className="brand-subtitle">Intelligent Mobility</p>
      </div>
      <div className="status" role="status">
        <span className={`status-dot status-dot-${status.tone}`} aria-hidden="true" />
        <span className="status-label">{status.label}</span>
      </div>
    </header>
  )
}

export default Header
