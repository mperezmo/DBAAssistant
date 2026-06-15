import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import Gauge from '../components/Gauge.jsx';
import { getConnections, getPerfMetrics, getActiveSessions, getTopQueries } from '../api.js';

function Counter({ label, value, sub, color }) {
  return (
    <div style={{ borderTop: '1px solid var(--line-strong)', padding: '14px 0 0', textAlign: 'center' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--fg-faint)', marginBottom: 6 }}>{label}</div>
      <div className="metric-large" style={{ fontSize: 38, color: color || 'var(--fg)' }}>{value ?? '—'}</div>
      {sub && <div style={{ fontSize: 11.5, color: 'var(--fg-muted)', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// Una sesión es anomalía si está bloqueada, consume mucha CPU o corre hace mucho.
function anomalyOf(s) {
  if (s.blocking_session_id) return { label: 'bloqueada', cls: 'tag-red' };
  if ((s.cpu_ms ?? 0) > 10000) return { label: 'CPU alta', cls: 'tag-yellow' };
  if ((s.elapsed_ms ?? 0) > 60000) return { label: 'long-running', cls: 'tag-yellow' };
  return null;
}

export default function MonitorPage({ connectionId, onSelectConnection, goTo }) {
  const { getAccessTokenSilently } = useAuth0();
  const [connections, setConnections] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [topq, setTopq] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [auto, setAuto] = useState(false);
  const [lastRead, setLastRead] = useState(null);
  const timer = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessTokenSilently();
        setConnections(await getConnections(token));
      } catch { /* ignore */ }
    })();
  }, [getAccessTokenSilently]);

  const load = useCallback(async () => {
    if (!connectionId) { setMetrics(null); setSessions([]); setTopq([]); return; }
    setLoading(true);
    setError('');
    try {
      const token = await getAccessTokenSilently();
      const [m, s, q] = await Promise.all([
        getPerfMetrics(token, connectionId),
        getActiveSessions(token, connectionId),
        getTopQueries(token, connectionId),
      ]);
      setMetrics(m); setSessions(s); setTopq(q);
      setLastRead(new Date());
    } catch (e) {
      setError(e.message);
      setMetrics(null); setSessions([]); setTopq([]);
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently, connectionId]);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh cada 10s
  useEffect(() => {
    if (auto && connectionId) {
      timer.current = setInterval(load, 10000);
      return () => clearInterval(timer.current);
    }
  }, [auto, connectionId, load]);

  const anomalies = sessions.filter(anomalyOf).length;
  const maxCpu = Math.max(1, ...topq.map((q) => q.total_cpu_ms));

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Monitoreo · DMVs en vivo</div>
        <h1 className="page-title">Panel de <em>instrumentos</em></h1>
        <p className="page-subtitle">Salud y rendimiento del motor SQL Server de la conexión seleccionada.</p>
      </div>

      {/* Selector de conexión */}
      <div className="row" style={{ marginBottom: 18, gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Conexión:</span>
        <select
          value={connectionId || ''}
          onChange={(e) => onSelectConnection(e.target.value || null)}
          style={{ padding: '7px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)' }}
        >
          <option value="">— Elegí una conexión —</option>
          {connections.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.database})</option>)}
        </select>
        <button className="btn btn-ghost btn-sm" onClick={() => goTo('admin')}><Icon name="settings" size={13} /> Gestionar</button>
        {connectionId && <button className="btn btn-ghost btn-sm" onClick={load}><Icon name="refresh" size={13} /> Refrescar</button>}
        {connectionId && (
          <button className={`btn btn-sm ${auto ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setAuto((a) => !a)}>
            {auto ? 'Auto 10s ✓' : 'Auto 10s'}
          </button>
        )}
      </div>

      {error && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}>
          <Icon name="warn" size={11} /> {error}
        </div>
      )}

      {connections.length === 0 && (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '48px 16px' }}>
            <div style={{ marginBottom: 10 }}><Icon name="monitor" size={28} /></div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>No agregaste ninguna conexión</div>
            <div style={{ color: 'var(--fg-muted)', fontSize: 13, marginBottom: 16 }}>Agregá tu SQL Server en el Panel Admin para monitorearlo.</div>
            <button className="btn btn-primary btn-sm" onClick={() => goTo('admin')}><Icon name="plus" size={13} /> Ir al Panel Admin</button>
          </div>
        </div>
      )}

      {connections.length > 0 && !connectionId && (
        <div className="card"><div className="card-body" style={{ color: 'var(--fg-muted)', fontSize: 13 }}>Elegí una conexión arriba para ver su rendimiento.</div></div>
      )}

      {connectionId && (
        <>
          {/* Instrumentos */}
          <div className="card" style={{ padding: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, paddingBottom: 16, borderBottom: '1px solid var(--line)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <span className="live-dot" />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--fg-muted)' }}>
                  {loading ? 'Leyendo…' : `Última lectura ${lastRead ? lastRead.toLocaleTimeString() : '—'}`}
                </span>
              </div>
              {anomalies > 0 && <span className="tag tag-red"><Icon name="warn" size={10} /> {anomalies} anomalía(s)</span>}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24, maxWidth: 460, margin: '0 auto' }}>
              <Gauge label="CPU (SQL)" value={metrics?.cpu_percent} unit="%" warn={70} crit={85} />
              <Gauge label="Memoria (SO)" value={metrics?.memory_percent} unit="%" warn={80} crit={90} />
            </div>

            <div className="divider" style={{ margin: '24px 0 18px' }} />

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24 }}>
              <Counter label="Sesiones (usuario)" value={metrics?.sessions} sub="is_user_process" />
              <Counter label="Requests activos" value={metrics?.active_requests} sub="en ejecución" />
              <Counter label="Conexiones" value={metrics?.connections} sub="dm_exec_connections" />
              <Counter label="Bloqueadas" value={metrics?.blocked} sub="locks activos" color={metrics?.blocked ? 'var(--terracotta)' : 'var(--sage)'} />
            </div>
          </div>

          {/* Sesiones + Top queries */}
          <div className="grid-2" style={{ marginTop: 20, gap: 20 }}>
            <div className="card">
              <div className="card-head">
                <div>
                  <div className="card-eyebrow">sys.dm_exec_requests</div>
                  <h3 className="card-title">Sesiones activas</h3>
                </div>
                <span className="tag">{sessions.length}</span>
              </div>
              <div style={{ overflow: 'auto' }}>
                <table className="data-table" style={{ fontSize: 12.5 }}>
                  <thead>
                    <tr><th>SID</th><th>Usuario</th><th>Estado</th><th style={{ textAlign: 'right' }}>CPU ms</th><th></th></tr>
                  </thead>
                  <tbody>
                    {sessions.length === 0 && <tr><td colSpan={5} style={{ color: 'var(--fg-faint)' }}>Sin sesiones de usuario activas.</td></tr>}
                    {sessions.map((s) => {
                      const a = anomalyOf(s);
                      return (
                        <tr key={s.session_id} title={s.query_text || ''}>
                          <td className="metric-mono" style={{ fontWeight: 600 }}>{s.session_id}</td>
                          <td style={{ fontSize: 12 }}>{s.login_name}</td>
                          <td className="metric-mono" style={{ fontSize: 11.5 }}>{s.status}</td>
                          <td className="metric-mono" style={{ textAlign: 'right' }}>{s.cpu_ms}</td>
                          <td>{a && <span className={`tag ${a.cls}`} style={{ padding: '1px 6px', fontSize: 9.5 }}>{a.label}</span>}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-head">
                <div>
                  <div className="card-eyebrow">sys.dm_exec_query_stats</div>
                  <h3 className="card-title">Consultas más costosas</h3>
                </div>
              </div>
              <div style={{ padding: '12px 20px' }}>
                {topq.length === 0 && <div style={{ color: 'var(--fg-faint)', fontSize: 12 }}>Sin datos de query stats.</div>}
                {topq.map((r, i) => (
                  <div key={i} style={{ padding: '10px 0', borderBottom: i === topq.length - 1 ? 'none' : '1px solid var(--line)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
                      <span className="metric-mono" style={{ fontSize: 11.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '70%' }}>{r.query_text || '—'}</span>
                      <span className="metric-mono" style={{ color: 'var(--fg-muted)', fontSize: 11 }}>{r.execution_count.toLocaleString()} exec</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ flex: 1, height: 5, background: 'var(--bg-sunk)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${(r.total_cpu_ms / maxCpu) * 100}%`, background: r.total_cpu_ms > 10000 ? 'var(--terracotta)' : 'var(--accent)' }} />
                      </div>
                      <span className="metric-mono" style={{ fontSize: 11, color: 'var(--fg-muted)', minWidth: 70, textAlign: 'right' }}>{r.total_cpu_ms.toLocaleString()} ms</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
