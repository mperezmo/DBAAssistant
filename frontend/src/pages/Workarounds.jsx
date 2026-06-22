import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import {
  getConnections, getDatabases, getWorkarounds, runWorkaround, createWorkaround, deleteWorkaround,
  getRules, createRule, updateRule, deleteRule, evaluateRules,
} from '../api.js';

const selectStyle = {
  padding: '7px 10px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)',
};
const SEV_TAG = { critical: 'tag-red', warning: 'tag-yellow', info: 'tag-blue' };
const CATEGORIES = ['Todos', 'Performance', 'Espacio', 'Mantenimiento', 'Disponibilidad'];

function formatWhen(iso) {
  if (!iso) return 'sin ejecuciones';
  try {
    return new Date(iso).toLocaleString('es-AR', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
}

export default function WorkaroundsPage({ env, connectionId, onSelectConnection, goTo }) {
  const { getAccessTokenSilently } = useAuth0();
  const [connections, setConnections] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [database, setDatabase] = useState('');
  const [catalog, setCatalog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [cat, setCat] = useState('Todos');
  const [q, setQ] = useState('');
  const [runWk, setRunWk] = useState(null);   // workaround abierto en el modal de ejecución
  const [showCreate, setShowCreate] = useState(false);
  const [showAuto, setShowAuto] = useState(false);

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
      } catch (e) { setError(e.message); }
    })();
  }, [connectionId, getAccessTokenSilently]);

  const loadCatalog = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const t = await getAccessTokenSilently();
      setCatalog(await getWorkarounds(t));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => { loadCatalog(); }, [loadCatalog]);

  const counts = useMemo(() => {
    const c = { Todos: catalog.length };
    for (const w of catalog) c[w.category] = (c[w.category] || 0) + 1;
    return c;
  }, [catalog]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return catalog.filter((w) =>
      (cat === 'Todos' || w.category === cat) &&
      (!needle || `${w.name} ${w.description} ${w.key}`.toLowerCase().includes(needle)));
  }, [catalog, cat, q]);

  const ready = Boolean(connectionId && database);

  async function handleDelete(key) {
    if (!window.confirm(`¿Borrar el workaround "${key}"? Esta acción no se puede deshacer.`)) return;
    try {
      const t = await getAccessTokenSilently();
      await deleteWorkaround(t, key);
      loadCatalog();
    } catch (e) { setError(e.message); }
  }

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Workarounds · biblioteca de remediación</div>
        <h1 className="page-title">Playbooks <em>pre-aprobados</em></h1>
        <p className="page-subtitle">
          Cada workaround se <strong>diagnostica</strong> (solo lectura) antes de <strong>aplicarse</strong> sobre
          la base elegida. Toda ejecución queda auditada.
        </p>
      </div>

      {/* Selector de conexión + base */}
      <div className="row" style={{ marginBottom: 16, gap: 10, flexWrap: 'wrap' }}>
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
        <button className="btn btn-ghost btn-sm" onClick={loadCatalog}><Icon name="refresh" size={13} /> Refrescar</button>
      </div>

      {!ready && (
        <div className="tag" style={{ display: 'inline-flex', marginBottom: 16, color: 'var(--fg-muted)' }}>
          <Icon name="info" size={11} /> Elegí una conexión y una base para poder ejecutar.
        </div>
      )}
      {error && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}>
          <Icon name="warn" size={11} /> {error}
        </div>
      )}

      {/* Toolbar: nuevo + filtros + búsqueda */}
      <div className="row" style={{ marginBottom: 20, gap: 10, flexWrap: 'wrap' }}>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}><Icon name="plus" size={14} /> Nuevo workaround</button>
        <button className={`btn ${showAuto ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setShowAuto((s) => !s)}>
          <Icon name="refresh" size={14} /> Automatización
        </button>
        {CATEGORIES.map((c) => (
          <button
            key={c}
            className={`btn btn-sm ${cat === c ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setCat(c)}
          >
            {c} · {counts[c] || 0}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        <div style={{ position: 'relative' }}>
          <input
            placeholder="Buscar workaround..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            style={{
              padding: '8px 12px 8px 32px', width: 240,
              border: '1px solid var(--line-strong)', borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-elev)', color: 'var(--fg)',
            }}
          />
          <span style={{ position: 'absolute', left: 10, top: 9, color: 'var(--fg-faint)' }}><Icon name="search" size={14} /></span>
        </div>
      </div>

      {showAuto && (
        <AutomationPanel
          catalog={catalog}
          connectionId={connectionId}
          database={database}
          getToken={getAccessTokenSilently}
          onRan={loadCatalog}
        />
      )}

      {loading && <div style={{ color: 'var(--fg-faint)' }}>Cargando catálogo…</div>}
      {!loading && filtered.length === 0 && (
        <div style={{ color: 'var(--fg-faint)' }}>No hay workarounds para este filtro.</div>
      )}

      <div className="grid-3" style={{ gap: 16 }}>
        {filtered.map((w) => (
          <WkCard key={w.key} w={w} onRun={() => setRunWk(w)} onDelete={() => handleDelete(w.key)} />
        ))}
      </div>

      {runWk && (
        <RunModal
          wk={runWk}
          env={env}
          connectionId={connectionId}
          database={database}
          ready={ready}
          getToken={getAccessTokenSilently}
          onClose={() => setRunWk(null)}
          onRan={loadCatalog}
        />
      )}
      {showCreate && (
        <CreateModal
          getToken={getAccessTokenSilently}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); loadCatalog(); }}
        />
      )}
    </div>
  );
}

function WkCard({ w, onRun, onDelete }) {
  return (
    <div className="card" style={{ padding: 18, position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
        <span className="metric-mono" style={{ fontSize: 11, color: 'var(--fg-faint)', letterSpacing: '0.08em' }}>{w.key}</span>
        <span className={`tag ${SEV_TAG[w.severity] || 'tag-blue'}`}>{w.severity}</span>
      </div>
      <h4 style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 500, margin: '0 0 6px' }}>{w.name}</h4>
      <p style={{ fontSize: 12.5, color: 'var(--fg-muted)', margin: '0 0 14px', minHeight: 36 }}>{w.description}</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        <span className="tag">{w.category}</span>
        {w.builtin ? <span className="tag">built-in</span> : <span className="tag tag-blue">custom</span>}
        {w.requires_server_state && <span className="tag" title="El login necesita VIEW SERVER STATE">VIEW SERVER STATE</span>}
      </div>
      <div className="divider" style={{ margin: '12px 0' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11.5, color: 'var(--fg-faint)', fontFamily: 'var(--font-mono)' }}>
        <span>{w.runs} ejecuciones · {formatWhen(w.last_run)}</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {!w.builtin && (
            <button className="btn btn-ghost btn-sm" style={{ padding: '4px 8px' }} title="Borrar" onClick={onDelete}>
              <Icon name="x" size={12} />
            </button>
          )}
          <button className="btn btn-ghost btn-sm" style={{ padding: '4px 10px' }} onClick={onRun}>
            <Icon name="play" size={12} /> Ejecutar
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal genérico (overlay) ─────────────────────────────────────────────────
function Modal({ title, eyebrow, onClose, children, width = 720 }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 50,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '6vh 16px', overflowY: 'auto',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{ width: '100%', maxWidth: width, background: 'var(--bg-elev)' }}
      >
        <div className="card-head">
          <div>
            {eyebrow && <div className="card-eyebrow">{eyebrow}</div>}
            <h3 className="card-title">{title}</h3>
          </div>
          <button className="icon-btn" onClick={onClose} title="Cerrar"><Icon name="x" size={16} /></button>
        </div>
        <div className="card-body">{children}</div>
      </div>
    </div>
  );
}

function ResultTable({ columns, rows, truncated }) {
  if (!columns || columns.length === 0) return null;
  return (
    <div style={{ overflow: 'auto', maxHeight: 320, border: '1px solid var(--line)', borderRadius: 'var(--radius-sm)' }}>
      <table className="data-table" style={{ fontSize: 12 }}>
        <thead>
          <tr>{columns.map((c, i) => <th key={i}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={columns.length} style={{ color: 'var(--fg-faint)' }}>Sin filas: nada que remediar. 👌</td></tr>
          )}
          {rows.map((r, ri) => (
            <tr key={ri}>{r.map((v, ci) => <td key={ci} className="metric-mono">{v === null ? '—' : String(v)}</td>)}</tr>
          ))}
        </tbody>
      </table>
      {truncated && <div style={{ padding: '6px 10px', fontSize: 11, color: 'var(--fg-faint)' }}>Resultado truncado a 1000 filas.</div>}
    </div>
  );
}

function SqlBlock({ label, sql }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="card-eyebrow" style={{ marginBottom: 6 }}>{label}</div>
      <pre style={{
        margin: 0, padding: '12px 14px', fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.55,
        background: 'var(--bg-sunk)', borderRadius: 'var(--radius-sm)', maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap',
      }}>{sql}</pre>
    </div>
  );
}

function RunModal({ wk, env, connectionId, database, ready, getToken, onClose, onRan }) {
  const [busy, setBusy] = useState('');     // 'diagnose' | 'apply' | ''
  const [diag, setDiag] = useState(null);   // {columns, rows, truncated}
  const [applied, setApplied] = useState(null); // {affected_rows, message, elapsed_ms}
  const [err, setErr] = useState('');

  async function run(mode) {
    setErr('');
    if (mode === 'apply' && !window.confirm(
      `Vas a APLICAR "${wk.name}" sobre ${database} (${env}). Es una acción real sobre la base. ¿Continuar?`)) return;
    setBusy(mode);
    try {
      const t = await getToken();
      const res = await runWorkaround(t, wk.key, { connection_id: connectionId, database, mode });
      if (mode === 'diagnose') setDiag(res);
      else { setApplied(res); setDiag(null); }
      onRan();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy('');
    }
  }

  return (
    <Modal eyebrow={`Workaround · ${wk.key}`} title={wk.name} onClose={onClose}>
      <p style={{ fontSize: 13, color: 'var(--fg-muted)', marginTop: 0 }}>{wk.description}</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        <span className={`tag ${SEV_TAG[wk.severity] || 'tag-blue'}`}>{wk.severity}</span>
        <span className="tag">{wk.category}</span>
        {wk.requires_server_state && <span className="tag tag-yellow">requiere VIEW SERVER STATE</span>}
      </div>

      {!ready && (
        <div className="tag tag-yellow" style={{ display: 'inline-flex', marginBottom: 14 }}>
          <Icon name="warn" size={11} /> Elegí una conexión y una base antes de ejecutar.
        </div>
      )}

      {wk.kind === 'service' ? (
        <div className="tag tag-blue" style={{ display: 'inline-flex', marginBottom: 12 }}>
          <Icon name="info" size={11} /> Acción a nivel Windows vía WinRM (no usa T-SQL). Configurá el control de host en el Panel Admin.
        </div>
      ) : (
        <>
          {wk.diagnose_sql && <SqlBlock label="Diagnóstico (solo lectura)" sql={wk.diagnose_sql} />}
          {wk.apply_sql && <SqlBlock label="Remediación (al aplicar)" sql={wk.apply_sql} />}
        </>
      )}

      <div style={{ display: 'flex', gap: 10, margin: '4px 0 14px' }}>
        <button className="btn btn-ghost" disabled={!ready || busy} onClick={() => run('diagnose')}>
          <Icon name="eye" size={14} /> {busy === 'diagnose' ? 'Diagnosticando…' : 'Diagnosticar'}
        </button>
        <button className="btn btn-primary" disabled={!ready || busy} onClick={() => run('apply')}>
          <Icon name="play" size={14} /> {busy === 'apply' ? 'Aplicando…' : `Aplicar sobre ${env}`}
        </button>
      </div>

      {err && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 12 }}>
          <Icon name="warn" size={11} /> {err}
        </div>
      )}

      {diag && (
        <div style={{ marginBottom: 8 }}>
          <div className="card-eyebrow" style={{ marginBottom: 6 }}>
            Diagnóstico · {diag.rows.length} problema(s){diag.message ? ` · ${diag.message}` : ''}
          </div>
          <ResultTable columns={diag.columns} rows={diag.rows} truncated={diag.truncated} />
        </div>
      )}
      {applied && (
        <div className="tag tag-green" style={{ display: 'inline-flex' }}>
          <Icon name="check" size={11} /> {applied.message} {applied.affected_rows != null && `· ${applied.affected_rows} filas`}
          {applied.elapsed_ms != null && ` · ${applied.elapsed_ms} ms`}
        </div>
      )}
    </Modal>
  );
}

function AutomationPanel({ catalog, connectionId, database, getToken, onRan }) {
  const [rules, setRules] = useState([]);
  const [err, setErr] = useState('');
  const [evalRes, setEvalRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', workaround_key: '', min_rows: 1, cooldown_seconds: 300 });

  const loadRules = useCallback(async () => {
    setErr('');
    try {
      const t = await getToken();
      setRules(await getRules(t));
    } catch (e) { setErr(e.message); }
  }, [getToken]);

  useEffect(() => { loadRules(); }, [loadRules]);

  async function evaluate() {
    setBusy(true);
    setErr('');
    try {
      const t = await getToken();
      setEvalRes(await evaluateRules(t));
      await loadRules();
      onRan();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  async function toggle(r) {
    try {
      const t = await getToken();
      await updateRule(t, r.id, { enabled: !r.enabled });
      loadRules();
    } catch (e) { setErr(e.message); }
  }

  async function remove(id) {
    if (!window.confirm('¿Borrar esta regla de automatización?')) return;
    try {
      const t = await getToken();
      await deleteRule(t, id);
      loadRules();
    } catch (e) { setErr(e.message); }
  }

  async function submit() {
    setBusy(true);
    setErr('');
    try {
      const t = await getToken();
      await createRule(t, {
        ...form, min_rows: Number(form.min_rows), cooldown_seconds: Number(form.cooldown_seconds),
        connection_id: connectionId, database: database || '',
      });
      setShowForm(false);
      setForm({ name: '', workaround_key: '', min_rows: 1, cooldown_seconds: 300 });
      loadRules();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div className="card-head">
        <div>
          <div className="card-eyebrow">Automatización · reglas "si y solo si"</div>
          <h3 className="card-title">Auto-remediación</h3>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowForm((s) => !s)} disabled={!connectionId} title={!connectionId ? 'Elegí una conexión arriba' : ''}>
            <Icon name="plus" size={13} /> Nueva regla
          </button>
          <button className="btn btn-primary btn-sm" onClick={evaluate} disabled={busy}>
            <Icon name="play" size={13} /> {busy ? 'Evaluando…' : 'Evaluar ahora'}
          </button>
        </div>
      </div>

      <div className="card-body">
        <div style={{ fontSize: 12, color: 'var(--fg-muted)', marginBottom: 12 }}>
          Cada regla corre el <strong>diagnóstico</strong> del workaround; si detecta ≥ umbral problemas, <strong>aplica</strong> la
          remediación. "Evaluar ahora" las corre todas. El scheduler automático (cada N seg) es opt-in por <span className="metric-mono">AUTOMATION_ENABLED</span>.
        </div>

        {err && <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 12 }}><Icon name="warn" size={11} /> {err}</div>}

        {showForm && (
          <div style={{ background: 'var(--bg-sunk)', borderRadius: 'var(--radius-sm)', padding: 14, marginBottom: 14 }}>
            <div className="grid-3" style={{ gap: 12 }}>
              <div className="field"><label>Nombre</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Reiniciar SQL si cae" /></div>
              <div className="field"><label>Workaround</label>
                <select value={form.workaround_key} onChange={(e) => setForm({ ...form, workaround_key: e.target.value })}>
                  <option value="">— Elegí —</option>
                  {catalog.map((w) => <option key={w.key} value={w.key}>{w.name}</option>)}
                </select>
              </div>
              <div className="field"><label>Umbral (filas)</label><input value={form.min_rows} onChange={(e) => setForm({ ...form, min_rows: e.target.value })} /></div>
              <div className="field"><label>Cooldown (seg)</label><input value={form.cooldown_seconds} onChange={(e) => setForm({ ...form, cooldown_seconds: e.target.value })} /></div>
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--fg-faint)', margin: '8px 0' }}>
              Se crea sobre la conexión activa{database ? <> y la base <strong>{database}</strong></> : ' (los de servicio no usan base)'}.
            </div>
            <div className="row" style={{ gap: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={submit} disabled={busy || !form.name || !form.workaround_key}>Crear regla</button>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowForm(false)}>Cancelar</button>
            </div>
          </div>
        )}

        {evalRes && (
          <div style={{ marginBottom: 14 }}>
            <div className="card-eyebrow" style={{ marginBottom: 6 }}>Última evaluación · {evalRes.filter((r) => r.triggered).length} disparada(s) de {evalRes.length}</div>
            {evalRes.length === 0 && <div style={{ fontSize: 12, color: 'var(--fg-faint)' }}>No hay reglas habilitadas.</div>}
            {evalRes.map((r) => (
              <div key={r.rule_id} style={{ fontSize: 12, fontFamily: 'var(--font-mono)', padding: '2px 0' }}>
                <span className={`tag ${r.error ? 'tag-red' : r.triggered ? 'tag-green' : ''}`} style={{ display: 'inline-flex' }}>
                  {r.error ? 'error' : r.triggered ? 'disparada' : (r.checked ? 'sin acción' : 'saltada')}
                </span>{' '}
                {r.name} · {r.error || r.status || ''}
              </div>
            ))}
          </div>
        )}

        <div style={{ overflow: 'auto' }}>
          <table className="data-table" style={{ fontSize: 12.5 }}>
            <thead>
              <tr><th>Regla</th><th>Workaround</th><th>Base</th><th style={{ textAlign: 'right' }}>Umbral</th><th style={{ textAlign: 'right' }}>Cooldown</th><th>Última corrida</th><th>Habilitada</th><th></th></tr>
            </thead>
            <tbody>
              {rules.length === 0 && <tr><td colSpan={8} style={{ color: 'var(--fg-faint)' }}>No hay reglas. Creá una con "Nueva regla".</td></tr>}
              {rules.map((r) => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 600 }}>{r.name}</td>
                  <td className="metric-mono" style={{ fontSize: 11.5 }}>{r.workaround_key}</td>
                  <td className="metric-mono" style={{ fontSize: 11.5, color: 'var(--fg-muted)' }}>{r.database || '—'}</td>
                  <td className="metric-mono" style={{ textAlign: 'right' }}>{r.min_rows}</td>
                  <td className="metric-mono" style={{ textAlign: 'right' }}>{r.cooldown_seconds}s</td>
                  <td className="metric-mono" style={{ fontSize: 11 }}>{r.last_triggered ? formatWhen(r.last_triggered) : '—'}{r.last_status ? ` · ${r.last_status}` : ''}</td>
                  <td>
                    <button className={`tag ${r.enabled ? 'tag-green' : ''}`} style={{ cursor: 'pointer' }} onClick={() => toggle(r)}>
                      {r.enabled ? 'sí' : 'no'}
                    </button>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button className="btn btn-ghost btn-sm" style={{ padding: '4px 8px' }} onClick={() => remove(r.id)} title="Borrar"><Icon name="x" size={12} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function CreateModal({ getToken, onClose, onCreated }) {
  const [form, setForm] = useState({
    key: '', name: '', description: '', category: 'Mantenimiento', severity: 'info',
    diagnose_sql: 'SELECT ...', apply_sql: '',
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit() {
    setErr('');
    setBusy(true);
    try {
      const t = await getToken();
      await createWorkaround(t, form);
      onCreated();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  const field = { ...selectStyle, width: '100%', boxSizing: 'border-box' };
  const area = { ...field, fontFamily: 'var(--font-mono)', fontSize: 12, minHeight: 80, resize: 'vertical' };
  const lbl = { display: 'block', fontSize: 12, color: 'var(--fg-muted)', margin: '10px 0 4px' };

  return (
    <Modal eyebrow="Nuevo workaround" title="Crear playbook custom" onClose={onClose} width={680}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <label style={lbl}>Key (único, sin espacios)</label>
          <input style={field} value={form.key} onChange={set('key')} placeholder="reindex_pedidos" />
        </div>
        <div>
          <label style={lbl}>Nombre</label>
          <input style={field} value={form.name} onChange={set('name')} placeholder="Reindexar pedidos" />
        </div>
      </div>
      <label style={lbl}>Descripción</label>
      <input style={field} value={form.description} onChange={set('description')} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div>
          <label style={lbl}>Categoría</label>
          <select style={field} value={form.category} onChange={set('category')}>
            {['Performance', 'Espacio', 'Mantenimiento'].map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label style={lbl}>Severidad</label>
          <select style={field} value={form.severity} onChange={set('severity')}>
            {['info', 'warning', 'critical'].map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
      </div>
      <label style={lbl}>SQL de diagnóstico (debe ser SELECT)</label>
      <textarea style={area} value={form.diagnose_sql} onChange={set('diagnose_sql')} />
      <label style={lbl}>SQL de remediación (se ejecuta al aplicar)</label>
      <textarea style={area} value={form.apply_sql} onChange={set('apply_sql')} placeholder="ALTER INDEX ... REBUILD;" />

      {err && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginTop: 12 }}>
          <Icon name="warn" size={11} /> {err}
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
        <button className="btn btn-ghost" onClick={onClose}>Cancelar</button>
        <button className="btn btn-primary" disabled={busy || !form.key || !form.name || !form.apply_sql} onClick={submit}>
          <Icon name="check" size={14} /> {busy ? 'Creando…' : 'Crear'}
        </button>
      </div>
    </Modal>
  );
}
