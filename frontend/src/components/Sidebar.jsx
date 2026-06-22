import { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Logo from './Logo.jsx';
import Icon from './Icon.jsx';
import { getAlertCount } from '../api.js';

const NAV_ITEMS = [
  { section: 'Operaciones', items: [
    { id: 'dashboard', label: 'Inicio', icon: 'home' },
    { id: 'chat', label: 'Chat IA', icon: 'chat' },
    { id: 'monitor', label: 'Monitoreo', icon: 'monitor' },
    { id: 'alerts', label: 'Alertas', icon: 'bell' },
    { id: 'workarounds', label: 'Workarounds', icon: 'play' },
    { id: 'sandbox', label: 'Sandbox', icon: 'sandbox' },
    { id: 'optimize', label: 'Optimización', icon: 'cpu' },
  ]},
  { section: 'Conocimiento', items: [
    { id: 'context', label: 'Contexto de Negocio', icon: 'book' },
    { id: 'schema', label: 'Esquema de BD', icon: 'table' },
    { id: 'audit', label: 'Auditoría', icon: 'audit' },
  ]},
  { section: 'Sistema', items: [
    { id: 'admin', label: 'Panel Admin', icon: 'settings' },
  ]},
];

// Sprint 3: Chat · 4: Esquema/Monitoreo/Auditoría/Admin · 5: Sandbox · 10: Workarounds · 11: Alertas.
const ENABLED = new Set(['chat', 'schema', 'monitor', 'sandbox', 'optimize', 'context', 'audit', 'admin', 'workarounds', 'alerts']);

function initialsOf(name) {
  const parts = (name || 'Usuario').trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]).join('').toUpperCase() || 'U';
}

export default function Sidebar({ active, onNav }) {
  const { user, logout, getAccessTokenSilently } = useAuth0();
  const name = user?.name || user?.email || 'Usuario';
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const t = await getAccessTokenSilently();
        const { active: n } = await getAlertCount(t);
        if (alive) setAlertCount(n || 0);
      } catch { /* ignore */ }
    })();
    return () => { alive = false; };
  }, [getAccessTokenSilently, active]);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Logo size={36} />
        <div>
          <div className="sidebar-brand-name">DBA Assistant</div>
          <div className="sidebar-brand-tag">Console v1.0</div>
        </div>
      </div>

      {NAV_ITEMS.map((sec) => (
        <div className="nav-section" key={sec.section}>
          <div className="nav-section-title">{sec.section}</div>
          {sec.items.map((it) => {
            const enabled = ENABLED.has(it.id);
            return (
              <button
                key={it.id}
                className={`nav-item ${active === it.id ? 'active' : ''} ${!enabled ? 'disabled' : ''}`}
                onClick={() => enabled && onNav(it.id)}
                title={!enabled ? 'Disponible en próximos sprints' : ''}
              >
                <Icon name={it.icon} size={16} />
                <span>{it.label}</span>
                {it.id === 'alerts' && alertCount > 0 && (
                  <span style={{
                    marginLeft: 'auto', background: 'var(--terracotta)', color: '#fff',
                    fontSize: 10, fontWeight: 700, borderRadius: 10, padding: '1px 7px',
                    fontFamily: 'var(--font-mono)',
                  }}>{alertCount}</span>
                )}
              </button>
            );
          })}
        </div>
      ))}

      <div className="sidebar-foot">
        <div
          className="user-card"
          onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
          title="Cerrar sesión"
        >
          <div className="user-avatar">{initialsOf(name)}</div>
          <div className="user-info">
            <div className="user-name">{name}</div>
            <div className="user-role">Cerrar sesión</div>
          </div>
          <Icon name="chevron" size={14} />
        </div>
      </div>
    </aside>
  );
}
