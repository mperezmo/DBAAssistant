import { useState, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import { getConnections, getDatabases, generateSql, executeSql, getQueryHistory } from '../api.js';

const selectStyle = {
  padding: '7px 10px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)',
};

export default function SandboxPage({ connectionId, onSelectConnection, goTo }) {
  const { getAccessTokenSilently } = useAuth0();
  const [connections, setConnections] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [database, setDatabase] = useState('');
  const [prompt, setPrompt] = useState('');
  const [sql, setSql] = useState('SELECT TOP 100 * FROM dbo.clientes;');
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState('');
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

  const loadHistory = useCallback(async () => {
    try {
      const t = await getAccessTokenSilently();
      setHistory(await getQueryHistory(t));
    } catch { /* ignore */ }
  }, [getAccessTokenSilently]);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  async function onGenerate() {
    if (!prompt.trim()) return;
    setBusy('gen');
    setError('');
    try {
      const t = await getAccessTokenSilently();
      const r = await generateSql(t, { prompt, connection_id: connectionId, database });
      setSql(r.sql);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  async function run(mode) {
    if (!connectionId || !database) { setError('Elegí una instancia y una base.'); return; }
    if (mode === 'apply' && !window.confirm('¿Aplicar los cambios? Esto hace COMMIT en la base seleccionada.')) return;
    setBusy(mode);
    setError('');
    setResult(null);
    try {
      const t = await getAccessTokenSilently();
      const r = await executeSql(t, { connection_id: connectionId, database, sql, mode });
      setResult(r);
      loadHistory();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  const ready = connectionId && database;

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">SQL · generación y ejecución controlada</div>
        <h1 className="page-title">Sandbox <em>de consultas</em></h1>
        <p className="page-subtitle">Generá T-SQL con IA, vista previa con rollback y ejecución con commit sobre la base elegida.</p>
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
      </div>

      {error && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}>
          <Icon name="warn" size={11} /> {error}
        </div>
      )}

      {connections.length === 0 ? (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '48px 16px' }}>
            <div style={{ marginBottom: 10 }}><Icon name="sandbox" size={28} /></div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>No agregaste ninguna conexión</div>
            <div style={{ color: 'var(--fg-muted)', fontSize: 13, marginBottom: 16 }}>Agregá una instancia en el Panel Admin para ejecutar SQL.</div>
            <button className="btn btn-primary btn-sm" onClick={() => goTo('admin')}><Icon name="plus" size={13} /> Ir al Panel Admin</button>
          </div>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 20, alignItems: 'start' }}>
            {/* Editor */}
            <div className="card">
              <div className="card-head">
                <div>
                  <div className="card-eyebrow">Editor T-SQL</div>
                  <h3 className="card-title">Consulta</h3>
                </div>
              </div>
              <div className="card-body">
                <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                  <input
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') onGenerate(); }}
                    placeholder="Describí en criollo lo que querés (genera T-SQL con IA)…"
                    style={{ flex: 1, padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)' }}
                  />
                  <button className="btn btn-ghost btn-sm" onClick={onGenerate} disabled={busy === 'gen' || !prompt.trim()}>
                    <Icon name="chat" size={13} /> {busy === 'gen' ? 'Generando…' : 'Generar con IA'}
                  </button>
                </div>
                <textarea
                  value={sql}
                  onChange={(e) => setSql(e.target.value)}
                  spellCheck={false}
                  style={{
                    width: '100%', minHeight: 240, resize: 'vertical',
                    fontFamily: 'var(--font-mono)', fontSize: 12.5, lineHeight: 1.7,
                    padding: '12px 14px', borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--line-strong)', background: 'var(--bg-sunk)', color: 'var(--fg)',
                  }}
                />
              </div>
              <div className="card-foot">
                <span>Solo lectura: SELECT corre directo. Escrituras: vista previa → ejecutar.</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => run('preview')} disabled={!ready || !!busy}>
                    <Icon name="eye" size={13} /> {busy === 'preview' ? '…' : 'Vista previa'}
                  </button>
                  <button className="btn btn-primary btn-sm" onClick={() => run('apply')} disabled={!ready || !!busy}>
                    <Icon name="play" size={13} /> {busy === 'apply' ? '…' : 'Ejecutar'}
                  </button>
                </div>
              </div>
            </div>

            {/* Resultado */}
            <div className="card">
              <div className="card-head">
                <div>
                  <div className="card-eyebrow">Resultado</div>
                  <h3 className="card-title">{result ? (result.kind === 'select' ? 'Filas' : 'Ejecución') : 'Sin ejecutar'}</h3>
                </div>
                {result && result.kind === 'write' && (
                  <span className={`tag ${result.committed ? 'tag-green' : 'tag-yellow'}`}>
                    {result.committed ? 'APLICADO (commit)' : 'VISTA PREVIA (rollback)'}
                  </span>
                )}
              </div>
              <div className="card-body">
                {!result && <div style={{ color: 'var(--fg-faint)', fontSize: 13 }}>Ejecutá una consulta para ver el resultado.</div>}

                {result?.warnings?.length > 0 && (
                  <div style={{ marginBottom: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {result.warnings.map((w, i) => (
                      <span key={i} className="tag tag-yellow" style={{ display: 'inline-flex' }}><Icon name="warn" size={11} /> {w}</span>
                    ))}
                  </div>
                )}

                {result?.kind === 'write' && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 14px', fontSize: 13 }}>
                    <span style={{ color: 'var(--fg-muted)' }}>Filas afectadas</span>
                    <strong className="metric-mono">{result.affected_rows ?? '—'}</strong>
                    <span style={{ color: 'var(--fg-muted)' }}>Estado</span>
                    <strong className="metric-mono">{result.committed ? 'COMMIT' : 'ROLLBACK (no aplicado)'}</strong>
                    <span style={{ color: 'var(--fg-muted)' }}>Tiempo</span>
                    <strong className="metric-mono">{result.elapsed_ms} ms</strong>
                  </div>
                )}

                {result?.kind === 'select' && (
                  <>
                    <div style={{ fontSize: 11.5, color: 'var(--fg-muted)', marginBottom: 8 }}>
                      {result.rows.length} fila(s) · {result.elapsed_ms} ms
                    </div>
                    <div style={{ overflow: 'auto', maxHeight: 360 }}>
                      <table className="data-table" style={{ fontSize: 12 }}>
                        <thead>
                          <tr>{result.columns.map((c) => <th key={c}>{c}</th>)}</tr>
                        </thead>
                        <tbody>
                          {result.rows.length === 0 && <tr><td colSpan={result.columns.length} style={{ color: 'var(--fg-faint)' }}>Sin filas.</td></tr>}
                          {result.rows.map((row, i) => (
                            <tr key={i}>
                              {row.map((v, j) => <td key={j} className="metric-mono" style={{ fontSize: 11.5 }}>{v === null ? 'NULL' : String(v)}</td>)}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Historial */}
          <div className="card" style={{ marginTop: 20 }}>
            <div className="card-head">
              <div>
                <div className="card-eyebrow">query_history · MongoDB</div>
                <h3 className="card-title">Historial de queries</h3>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={loadHistory}><Icon name="refresh" size={13} /> Refrescar</button>
            </div>
            <table className="data-table" style={{ fontSize: 12.5 }}>
              <thead>
                <tr><th>Timestamp</th><th>Usuario</th><th>Tipo</th><th>Estado</th><th>Filas</th><th>SQL</th></tr>
              </thead>
              <tbody>
                {history.length === 0 && <tr><td colSpan={6} style={{ color: 'var(--fg-faint)' }}>Sin queries todavía.</td></tr>}
                {history.map((h) => (
                  <tr key={h.id}>
                    <td className="metric-mono" style={{ fontSize: 11.5, color: 'var(--fg-faint)' }}>{new Date(h.timestamp).toLocaleString()}</td>
                    <td style={{ fontSize: 12 }}>{h.user}</td>
                    <td><span className="tag" style={{ padding: '1px 6px', fontSize: 9.5 }}>{h.kind || '—'}</span></td>
                    <td>
                      {!h.success
                        ? <span className="tag tag-red" style={{ padding: '1px 6px', fontSize: 9.5 }}>error</span>
                        : h.committed
                          ? <span className="tag tag-green" style={{ padding: '1px 6px', fontSize: 9.5 }}>commit</span>
                          : <span className="tag" style={{ padding: '1px 6px', fontSize: 9.5 }}>preview</span>}
                    </td>
                    <td className="metric-mono" style={{ fontSize: 12 }}>{h.affected_rows ?? '—'}</td>
                    <td className="metric-mono" style={{ fontSize: 11.5, color: 'var(--fg-muted)', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.sql}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
