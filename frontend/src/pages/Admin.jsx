import { useState, useEffect, useCallback, Fragment } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import {
  getHealth, getConnections, createConnection, testConnection, deleteConnection,
  getCacheStats, clearCache, getHostControl, putHostControl,
} from '../api.js';

const HC_EMPTY = { win_host: '', service_name: 'MSSQLSERVER', username: '', password: '', port: 5985, transport: 'ntlm' };

function ServiceCard({ name, ok }) {
  const c = ok ? 'var(--sage)' : 'var(--terracotta)';
  return (
    <div className="card" style={{ padding: 18 }}>
      <div className="row" style={{ marginBottom: 10 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: c }} />
        <strong style={{ fontSize: 14 }}>{name}</strong>
        <span style={{ flex: 1 }} />
        <span className="metric-mono" style={{ fontSize: 10, letterSpacing: '0.12em', color: c, textTransform: 'uppercase' }}>
          {ok ? 'online' : 'offline'}
        </span>
      </div>
      <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{ok ? 'Operativo' : 'Sin conexión'}</div>
    </div>
  );
}

const EMPTY = { name: '', host: 'host.docker.internal', port: 1433, username: '', password: '' };

export default function AdminPage({ connectionId, onSelectConnection, goTo }) {
  const { getAccessTokenSilently } = useAuth0();
  const [health, setHealth] = useState(null);
  const [conns, setConns] = useState([]);
  const [cacheStats, setCacheStats] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [testResult, setTestResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [hcFor, setHcFor] = useState(null);   // id de la conexión editando WinRM
  const [hc, setHc] = useState(HC_EMPTY);
  const [hcMsg, setHcMsg] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const token = await getAccessTokenSilently();
      const [h, c, cs] = await Promise.all([
        getHealth().catch(() => null),
        getConnections(token),
        getCacheStats(token).catch(() => null),
      ]);
      setHealth(h);
      setConns(c);
      setCacheStats(cs);
    } catch (e) {
      setError(e.message);
    }
  }, [getAccessTokenSilently]);

  async function onClearCache() {
    setBusy(true);
    setError('');
    try {
      const token = await getAccessTokenSilently();
      await clearCache(token);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { load(); }, [load]);

  function upd(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
    setTestResult(null);
  }

  async function onTest() {
    setBusy(true);
    setTestResult(null);
    setError('');
    try {
      const token = await getAccessTokenSilently();
      setTestResult(await testConnection(token, { ...form, port: Number(form.port) }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onSave() {
    setBusy(true);
    setError('');
    try {
      const token = await getAccessTokenSilently();
      const created = await createConnection(token, { ...form, port: Number(form.port) });
      setShowForm(false);
      setForm(EMPTY);
      setTestResult(null);
      await load();
      onSelectConnection(created.id);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id) {
    setBusy(true);
    setError('');
    try {
      const token = await getAccessTokenSilently();
      await deleteConnection(token, id);
      if (connectionId === id) onSelectConnection(null);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function openHostControl(id) {
    setHcMsg('');
    if (hcFor === id) { setHcFor(null); return; }
    setHcFor(id);
    setHc(HC_EMPTY);
    try {
      const token = await getAccessTokenSilently();
      const cfg = await getHostControl(token, id);
      setHc({ ...HC_EMPTY, ...cfg, password: '' });
      if (cfg.has_password) setHcMsg('Hay una contraseña guardada (dejá el campo vacío para conservarla).');
    } catch (e) { setError(e.message); }
  }

  async function saveHostControl(id) {
    setBusy(true);
    setHcMsg('');
    setError('');
    try {
      const token = await getAccessTokenSilently();
      await putHostControl(token, id, { ...hc, port: Number(hc.port) });
      setHcMsg('Configuración WinRM guardada.');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const services = [
    { name: 'SQL Server (app)', ok: health?.services?.sqlserver },
    { name: 'MongoDB', ok: health?.services?.mongo },
    { name: 'Redis', ok: health?.services?.redis },
  ];

  const canSave = form.name && form.host && form.username;

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Panel administrador · Sistema</div>
        <h1 className="page-title">Configuración <em>del sistema</em></h1>
        <p className="page-subtitle">Salud de los servicios y conexiones a las bases de datos a analizar.</p>
      </div>

      {error && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}>
          <Icon name="warn" size={11} /> {error}
        </div>
      )}

      <div className="grid-3" style={{ marginBottom: 20 }}>
        {services.map((s) => <ServiceCard key={s.name} name={s.name} ok={!!s.ok} />)}
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-head">
          <div>
            <div className="card-eyebrow">Caché · Redis</div>
            <h3 className="card-title">Rendimiento de caché</h3>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClearCache} disabled={busy}>
            <Icon name="refresh" size={13} /> Limpiar caché
          </button>
        </div>
        <div className="card-body">
          <div className="grid-4">
            <div><div className="card-eyebrow">Hits</div><div className="metric-large">{cacheStats?.hits ?? '—'}</div></div>
            <div><div className="card-eyebrow">Misses</div><div className="metric-large">{cacheStats?.misses ?? '—'}</div></div>
            <div><div className="card-eyebrow">Hit ratio</div><div className="metric-large">{cacheStats?.hit_ratio != null ? `${cacheStats.hit_ratio}%` : '—'}</div></div>
            <div><div className="card-eyebrow">Claves</div><div className="metric-large">{cacheStats?.keys ?? '—'}</div></div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-eyebrow">Conexiones SQL Server · {conns.length} instancia(s)</div>
            <h3 className="card-title">Bases de datos</h3>
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => { setShowForm((s) => !s); setTestResult(null); }}>
            <Icon name="plus" size={13} /> Nueva conexión
          </button>
        </div>

        {showForm && (
          <div className="card-body" style={{ borderBottom: '1px solid var(--line)', background: 'var(--bg-sunk)' }}>
            <div className="grid-3" style={{ gap: 12 }}>
              <div className="field"><label>Alias</label><input value={form.name} onChange={(e) => upd('name', e.target.value)} placeholder="Mi SQL local" /></div>
              <div className="field"><label>Host</label><input value={form.host} onChange={(e) => upd('host', e.target.value)} placeholder="host.docker.internal" /></div>
              <div className="field"><label>Puerto</label><input value={form.port} onChange={(e) => upd('port', e.target.value)} placeholder="1433" /></div>
              <div className="field"><label>Usuario</label><input value={form.username} onChange={(e) => upd('username', e.target.value)} placeholder="sa" /></div>
              <div className="field"><label>Contraseña</label><input type="password" value={form.password} onChange={(e) => upd('password', e.target.value)} /></div>
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--fg-faint)', marginTop: 4, marginBottom: 10 }}>
              La conexión es a la <strong>instancia</strong>. La base a analizar se elige luego en "Esquema de BD".
            </div>
            {testResult && (
              <div className={`tag ${testResult.ok ? 'tag-green' : 'tag-red'}`} style={{ display: 'inline-flex', marginBottom: 10 }}>
                <Icon name={testResult.ok ? 'check' : 'warn'} size={11} />{' '}
                {testResult.ok ? `Conecta a ${testResult.server}` : (testResult.detail || 'Falló la conexión')}
              </div>
            )}
            <div className="row" style={{ gap: 8 }}>
              <button className="btn btn-ghost btn-sm" onClick={onTest} disabled={busy || !canSave}>
                <Icon name="refresh" size={13} /> Probar
              </button>
              <button className="btn btn-primary btn-sm" onClick={onSave} disabled={busy || !canSave}>Guardar</button>
              <button className="btn btn-ghost btn-sm" onClick={() => { setShowForm(false); setForm(EMPTY); setTestResult(null); }}>Cancelar</button>
            </div>
          </div>
        )}

        <table className="data-table">
          <thead>
            <tr><th>Alias</th><th>Host</th><th>Usuario</th><th>Estado</th><th></th></tr>
          </thead>
          <tbody>
            {conns.length === 0 && (
              <tr><td colSpan={5} style={{ color: 'var(--fg-faint)' }}>No hay conexiones. Agregá una con "Nueva conexión".</td></tr>
            )}
            {conns.map((c) => (
              <Fragment key={c.id}>
                <tr>
                  <td className="metric-mono" style={{ fontWeight: 600 }}>{c.name}</td>
                  <td className="metric-mono" style={{ fontSize: 11.5, color: 'var(--fg-muted)' }}>{c.host}:{c.port}</td>
                  <td className="metric-mono" style={{ fontSize: 12 }}>{c.username}</td>
                  <td>{connectionId === c.id ? <span className="tag tag-blue">activa</span> : <span className="tag">—</span>}</td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button className="btn btn-ghost btn-sm" onClick={() => { onSelectConnection(c.id); goTo('schema'); }}>Usar</button>{' '}
                    <button className={`btn btn-sm ${hcFor === c.id ? 'btn-primary' : 'btn-ghost'}`} onClick={() => openHostControl(c.id)} title="Control de servicio Windows (WinRM)">WinRM</button>{' '}
                    <button className="btn btn-ghost btn-sm" onClick={() => onDelete(c.id)} disabled={busy} title="Borrar">
                      <Icon name="x" size={13} />
                    </button>
                  </td>
                </tr>
                {hcFor === c.id && (
                  <tr>
                    <td colSpan={5} style={{ background: 'var(--bg-sunk)' }}>
                      <div className="card-eyebrow" style={{ marginBottom: 8 }}>Control de host · WinRM (para "Iniciar servicio de SQL Server")</div>
                      <div className="grid-3" style={{ gap: 12 }}>
                        <div className="field"><label>Host WinRM</label><input value={hc.win_host} onChange={(e) => setHc({ ...hc, win_host: e.target.value })} placeholder={c.host} /></div>
                        <div className="field"><label>Servicio</label><input value={hc.service_name} onChange={(e) => setHc({ ...hc, service_name: e.target.value })} placeholder="MSSQLSERVER" /></div>
                        <div className="field"><label>Puerto</label><input value={hc.port} onChange={(e) => setHc({ ...hc, port: e.target.value })} placeholder="5985" /></div>
                        <div className="field"><label>Usuario Windows</label><input value={hc.username} onChange={(e) => setHc({ ...hc, username: e.target.value })} placeholder=".\\Administrador" /></div>
                        <div className="field"><label>Contraseña</label><input type="password" value={hc.password} onChange={(e) => setHc({ ...hc, password: e.target.value })} /></div>
                        <div className="field"><label>Transport</label>
                          <select value={hc.transport} onChange={(e) => setHc({ ...hc, transport: e.target.value })}>
                            <option value="ntlm">ntlm</option>
                            <option value="basic">basic</option>
                          </select>
                        </div>
                      </div>
                      <div style={{ fontSize: 11.5, color: 'var(--fg-faint)', margin: '8px 0' }}>
                        Requiere <strong>Enable-PSRemoting</strong> en la máquina Windows y un usuario con permiso sobre servicios.
                        Instancia con nombre: usá <span className="metric-mono">MSSQL$NOMBRE</span>.
                      </div>
                      {hcMsg && <div className="tag tag-green" style={{ display: 'inline-flex', marginBottom: 8 }}><Icon name="check" size={11} /> {hcMsg}</div>}
                      <div className="row" style={{ gap: 8 }}>
                        <button className="btn btn-primary btn-sm" onClick={() => saveHostControl(c.id)} disabled={busy || !hc.service_name || !hc.username}>Guardar WinRM</button>
                        <button className="btn btn-ghost btn-sm" onClick={() => setHcFor(null)}>Cerrar</button>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
