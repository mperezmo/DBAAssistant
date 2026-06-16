import Icon from './Icon.jsx';

function EnvPill({ env }) {
  return (
    <button className="env-pill" data-env={env}>
      <span className="dot"></span>
      Ambiente · {env}
      <Icon name="down" size={12} />
    </button>
  );
}

const LABELS = { chat: 'Chat IA', schema: 'Esquema de BD', monitor: 'Monitoreo', audit: 'Auditoría', admin: 'Panel Admin' };

export default function Topbar({ active, env }) {
  return (
    <header className="topbar">
      <div className="crumbs">
        <span>DBA Assistant</span>
        <span className="sep">/</span>
        <strong>{LABELS[active] || 'Chat IA'}</strong>
      </div>
      <div className="topbar-spacer" />
      <div
        className="row"
        style={{ gap: 14, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--fg-faint)', letterSpacing: '0.08em', textTransform: 'uppercase' }}
      >
        <span className="live-dot" />
        <span>Conectado · DBA Assistant API</span>
      </div>
      <EnvPill env={env} />
      <button className="icon-btn"><Icon name="search" size={16} /></button>
      <button className="icon-btn" title="Alertas">
        <Icon name="bell" size={16} />
        <span className="pulse-dot" />
      </button>
    </header>
  );
}
