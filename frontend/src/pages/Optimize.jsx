import { useState, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import { getConnections, getDatabases, getMissingIndexes, getUnusedIndexes } from '../api.js';

const selectStyle = {
  padding: '7px 10px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)',
};

function CopyBtn({ text }) {
  const [done, setDone] = useState(false);
  return (
    <button
      className="btn btn-ghost btn-sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        } catch { /* ignore */ }
      }}
    >
      <Icon name={done ? 'check' : 'code'} size={12} /> {done ? 'Copiado' : 'Copiar'}
    </button>
  );
}

export default function OptimizePage({ connectionId, onSelectConnection, goTo }) {
  const { getAccessTokenSilently } = useAuth0();
  const [connections, setConnections] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [database, setDatabase] = useState('');
  const [missing, setMissing] = useState([]);
  const [unused, setUnused] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const t = await getAccessTokenSilently();
        setConnections(await getConnections(t));
      } catch { /* ignore */ }
    })();
  }, [getAccessTokenSilently]);

  useEffect(() => {
    setDatabase('');
    setDatabases([]);
    if (!connectionId) return;
    (async () => {
      try {
        const t = await getAccessTokenSilently();
        const dbs = await getDatabases(t, connectionId);
        setDatabases(dbs);
        if (dbs.length) setDatabase(dbs[0]);
      } catch (e) {
        setError(e.message);
      }
    })();
  }, [connectionId, getAccessTokenSilently]);

  const load = useCallback(async () => {
    if (!connectionId || !database) { setMissing([]); setUnused([]); return; }
    setLoading(true);
    setError('');
    try {
      const t = await getAccessTokenSilently();
      const [mi, ui] = await Promise.all([
        getMissingIndexes(t, connectionId, database),
        getUnusedIndexes(t, connectionId, database),
      ]);
      setMissing(mi);
      setUnused(ui);
    } catch (e) {
      setError(e.message);
      setMissing([]);
      setUnused([]);
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently, connectionId, database]);

  useEffect(() => { load(); }, [load]);

  const ready = connectionId && database;

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Optimización · índices</div>
        <h1 className="page-title">Recomendaciones de <em>índices</em></h1>
        <p className="page-subtitle">Índices faltantes (con CREATE sugerido) e índices sin uso (candidatos a eliminar), según las DMVs.</p>
      </div>

      <div className="row" style={{ marginBottom: 18, gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Conexión:</span>
        <select value={connectionId || ''} onChange={(e) => onSelectConnection(e.target.value || null)} style={selectStyle}>
          <option value="">— Elegí una instancia —</option>
          {connections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        {connectionId && (
          <>
            <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Base:</span>
            <select value={database} onChange={(e) => setDatabase(e.target.value)} style={selectStyle} disabled={databases.length === 0}>
              {databases.length === 0 && <option value="">(sin bases)</option>}
              {databases.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </>
        )}
        <button className="btn btn-ghost btn-sm" onClick={() => goTo('admin')}><Icon name="settings" size={13} /> Gestionar</button>
        {ready && <button className="btn btn-ghost btn-sm" onClick={load}><Icon name="refresh" size={13} /> Refrescar</button>}
      </div>

      {error && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}>
          <Icon name="warn" size={11} /> {error}
        </div>
      )}

      {connections.length === 0 && (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '48px 16px' }}>
            <div style={{ marginBottom: 10 }}><Icon name="cpu" size={28} /></div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>No agregaste ninguna conexión</div>
            <div style={{ color: 'var(--fg-muted)', fontSize: 13, marginBottom: 16 }}>Agregá una instancia en el Panel Admin.</div>
            <button className="btn btn-primary btn-sm" onClick={() => goTo('admin')}><Icon name="plus" size={13} /> Ir al Panel Admin</button>
          </div>
        </div>
      )}

      {ready && (
        <>
          {/* Índices faltantes */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-head">
              <div>
                <div className="card-eyebrow">sys.dm_db_missing_index_*</div>
                <h3 className="card-title">Índices faltantes</h3>
              </div>
              <span className="tag tag-yellow">{missing.length}</span>
            </div>
            <div style={{ overflow: 'auto' }}>
              <table className="data-table" style={{ fontSize: 12.5 }}>
                <thead>
                  <tr><th>Tabla</th><th style={{ textAlign: 'right' }}>Impacto</th><th style={{ textAlign: 'right' }}>Usos</th><th>CREATE sugerido</th><th></th></tr>
                </thead>
                <tbody>
                  {loading && <tr><td colSpan={5} style={{ color: 'var(--fg-faint)' }}>Cargando…</td></tr>}
                  {!loading && missing.length === 0 && (
                    <tr><td colSpan={5} style={{ color: 'var(--fg-faint)' }}>Sin recomendaciones (no se registró carga que las amerite).</td></tr>
                  )}
                  {missing.map((m, i) => (
                    <tr key={i}>
                      <td className="metric-mono" style={{ fontWeight: 600 }}>{m.schema_name}.{m.table_name}</td>
                      <td className="metric-mono" style={{ textAlign: 'right' }}>{m.impact != null ? Math.round(m.impact).toLocaleString() : '—'}</td>
                      <td className="metric-mono" style={{ textAlign: 'right' }}>{m.uses ?? '—'}</td>
                      <td className="metric-mono" style={{ fontSize: 11, color: 'var(--fg-muted)', maxWidth: 460, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.create_statement}</td>
                      <td style={{ textAlign: 'right' }}><CopyBtn text={m.create_statement} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Índices sin uso */}
          <div className="card">
            <div className="card-head">
              <div>
                <div className="card-eyebrow">sys.dm_db_index_usage_stats</div>
                <h3 className="card-title">Índices sin uso</h3>
              </div>
              <span className="tag tag-red">{unused.length}</span>
            </div>
            <div style={{ overflow: 'auto' }}>
              <table className="data-table" style={{ fontSize: 12.5 }}>
                <thead>
                  <tr><th>Índice</th><th style={{ textAlign: 'right' }}>Seeks</th><th style={{ textAlign: 'right' }}>Scans</th><th style={{ textAlign: 'right' }}>Updates</th><th>DROP sugerido</th><th></th></tr>
                </thead>
                <tbody>
                  {loading && <tr><td colSpan={6} style={{ color: 'var(--fg-faint)' }}>Cargando…</td></tr>}
                  {!loading && unused.length === 0 && (
                    <tr><td colSpan={6} style={{ color: 'var(--fg-faint)' }}>No hay índices sin uso. 👌</td></tr>
                  )}
                  {unused.map((u, i) => (
                    <tr key={i}>
                      <td>
                        <span className="metric-mono" style={{ fontWeight: 600 }}>{u.index_name}</span>{' '}
                        <span style={{ color: 'var(--fg-faint)', fontSize: 11 }}>{u.schema_name}.{u.table_name}</span>
                      </td>
                      <td className="metric-mono" style={{ textAlign: 'right' }}>{u.user_seeks}</td>
                      <td className="metric-mono" style={{ textAlign: 'right' }}>{u.user_scans}</td>
                      <td className="metric-mono" style={{ textAlign: 'right', color: u.user_updates > 0 ? 'var(--terracotta)' : 'var(--fg)' }}>{u.user_updates}</td>
                      <td className="metric-mono" style={{ fontSize: 11, color: 'var(--fg-muted)', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{u.drop_statement}</td>
                      <td style={{ textAlign: 'right' }}><CopyBtn text={u.drop_statement} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
