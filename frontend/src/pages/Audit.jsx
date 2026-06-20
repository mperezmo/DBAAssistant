import { useState, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import { getAudit } from '../api.js';

const LABELS = {
  'connection.create': 'Alta conexión',
  'connection.delete': 'Baja conexión',
  'schema.view': 'Ver esquema',
  'query.execute': 'Ejecutar SQL',
  'context.update': 'Editar contexto',
};

const FILTERS = [
  { id: 'all', label: 'Todo', match: () => true },
  { id: 'conn', label: 'Conexiones', match: (a) => a.startsWith('connection.') },
  { id: 'schema', label: 'Esquema', match: (a) => a.startsWith('schema.') },
  { id: 'sql', label: 'SQL', match: (a) => a.startsWith('query.') },
];

export default function AuditPage() {
  const { getAccessTokenSilently } = useAuth0();
  const [entries, setEntries] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const token = await getAccessTokenSilently();
      setEntries(await getAudit(token));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => { load(); }, [load]);

  const active = FILTERS.find((x) => x.id === filter) || FILTERS[0];
  const rows = entries.filter((e) => active.match(e.action || ''));

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Auditoría · MongoDB</div>
        <h1 className="page-title">Bitácora <em>de acciones</em></h1>
        <p className="page-subtitle">Registro de quién hizo qué y cuándo: altas/bajas de conexiones y accesos a esquema.</p>
      </div>

      <div className="row" style={{ marginBottom: 18, gap: 8, flexWrap: 'wrap' }}>
        {FILTERS.map((f) => (
          <button key={f.id} className={`btn btn-sm ${filter === f.id ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFilter(f.id)}>
            {f.label}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        <button className="btn btn-ghost btn-sm" onClick={load}><Icon name="refresh" size={13} /> Refrescar</button>
      </div>

      {error && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}>
          <Icon name="warn" size={11} /> {error}
        </div>
      )}

      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-eyebrow">Registro · más recientes primero</div>
            <h3 className="card-title">Eventos</h3>
          </div>
          <span className="tag">{rows.length}</span>
        </div>
        <table className="data-table">
          <thead>
            <tr><th>Timestamp</th><th>Usuario</th><th>IP</th><th>Acción</th><th>Entidad</th><th>Detalle</th></tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={6} style={{ color: 'var(--fg-faint)' }}>Cargando…</td></tr>}
            {!loading && rows.length === 0 && (
              <tr><td colSpan={6} style={{ color: 'var(--fg-faint)' }}>Sin eventos registrados todavía.</td></tr>
            )}
            {rows.map((e) => (
              <tr key={e.id}>
                <td className="metric-mono" style={{ fontSize: 11.5, color: 'var(--fg-faint)' }}>
                  {new Date(e.timestamp).toLocaleString()}
                </td>
                <td><strong style={{ fontSize: 13 }}>{e.user}</strong></td>
                <td className="metric-mono" style={{ fontSize: 11.5, color: 'var(--fg-muted)' }}>{e.ip || '—'}</td>
                <td><span className="tag tag-blue" style={{ padding: '1px 7px', fontSize: 9.5 }}>{LABELS[e.action] || e.action}</span></td>
                <td className="metric-mono" style={{ fontSize: 12 }}>{e.target || '—'}</td>
                <td className="metric-mono" style={{ fontSize: 11.5, color: 'var(--fg-muted)' }}>{e.detail || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="card-foot">
          <span>{rows.length} registro(s)</span>
        </div>
      </div>
    </div>
  );
}
