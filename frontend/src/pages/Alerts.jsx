import { useState, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import {
  getConnections, getAlerts, patchAlert, evaluateAlerts, getAlertRules, seedAlertRules,
  createAlertRule, updateAlertRule, deleteAlertRule, getWorkarounds,
} from '../api.js';

const selectStyle = {
  padding: '7px 10px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)',
};
const SEV_TAG = { critical: 'tag-red', warning: 'tag-yellow', info: 'tag-blue' };
const SEV_COLOR = { critical: 'var(--terracotta)', warning: 'var(--mustard)', info: 'var(--accent)' };
const SEV_ORDER = { critical: 0, warning: 1, info: 2 };

const METRICS = [
  ['cpu_percent', 'CPU %'], ['memory_percent', 'Memoria %'], ['sessions', 'Sesiones'],
  ['active_requests', 'Requests activos'], ['connections', 'Conexiones'],
  ['blocked', 'Sesiones bloqueadas'], ['locks', 'Locks'],
  ['log_used_pct', 'Log usado % (por base)'],
  ['service_down', 'Servicio caído'], ['instance_unreachable', 'Instancia inalcanzable'],
];
const METRIC_LABEL = Object.fromEntries(METRICS);
const OP_SYM = { gt: '>', gte: '≥', lt: '<', lte: '≤' };

function fmtTime(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }); }
  catch { return ''; }
}

export default function AlertsPage({ connectionId, onSelectConnection, goTo }) {
  const { getAccessTokenSilently, user } = useAuth0();
  const [connections, setConnections] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [rules, setRules] = useState([]);
  const [wkKeys, setWkKeys] = useState([]);
  const [selId, setSelId] = useState(null);
  const [sevFilter, setSevFilter] = useState('all');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [evalMsg, setEvalMsg] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const t = await getAccessTokenSilently();
        const [conns, wks] = await Promise.all([getConnections(t), getWorkarounds(t).catch(() => [])]);
        setConnections(conns);
        setWkKeys(wks.map((w) => w.key));
      } catch { /* ignore */ }
    })();
  }, [getAccessTokenSilently]);

  const loadAlerts = useCallback(async () => {
    setError('');
    try {
      const t = await getAccessTokenSilently();
      const list = await getAlerts(t);
      list.sort((a, b) => (SEV_ORDER[a.severity] - SEV_ORDER[b.severity])
        || new Date(b.created_at) - new Date(a.created_at));
      setAlerts(list);
      setSelId((cur) => cur && list.some((a) => a.id === cur) ? cur : (list[0]?.id ?? null));
    } catch (e) { setError(e.message); }
  }, [getAccessTokenSilently]);

  const loadRules = useCallback(async () => {
    if (!connectionId) { setRules([]); return; }
    try {
      const t = await getAccessTokenSilently();
      setRules(await getAlertRules(t, connectionId));
    } catch (e) { setError(e.message); }
  }, [getAccessTokenSilently, connectionId]);

  useEffect(() => { loadAlerts(); }, [loadAlerts]);
  useEffect(() => { loadRules(); }, [loadRules]);

  async function evaluate() {
    setBusy(true);
    setError('');
    setEvalMsg('');
    try {
      const t = await getAccessTokenSilently();
      const res = await evaluateAlerts(t);
      const fired = res.filter((r) => r.breached).length;
      const auto = res.filter((r) => r.auto_remediated).length;
      setEvalMsg(`${res.length} reglas evaluadas · ${fired} en alerta${auto ? ` · ${auto} auto-remediadas` : ''}.`);
      await loadAlerts();
      await loadRules();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  async function act(id, body) {
    try {
      const t = await getAccessTokenSilently();
      await patchAlert(t, id, body);
      await loadAlerts();
    } catch (e) { setError(e.message); }
  }

  const shown = alerts.filter((a) => sevFilter === 'all' || a.severity === sevFilter);
  const sel = alerts.find((a) => a.id === selId) || null;
  const counts = { all: alerts.length, critical: 0, warning: 0, info: 0 };
  for (const a of alerts) counts[a.severity] = (counts[a.severity] || 0) + 1;

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Alertas · monitoreo por umbrales</div>
        <h1 className="page-title">Atención <em>requerida</em></h1>
        <p className="page-subtitle">
          {counts.all} alerta(s) activa(s){counts.critical ? ` · ${counts.critical} crítica(s)` : ''}.
          Las severidades respetan los umbrales configurados; al límite máximo se auto-remedia.
        </p>
      </div>

      <div className="row" style={{ marginBottom: 16, gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Conexión (reglas):</span>
        <select value={connectionId || ''} onChange={(e) => onSelectConnection(e.target.value || null)} style={selectStyle}>
          <option value="">— Elegí una instancia —</option>
          {connections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <button className="btn btn-primary btn-sm" onClick={evaluate} disabled={busy}>
          <Icon name="play" size={13} /> {busy ? 'Evaluando…' : 'Evaluar ahora'}
        </button>
        <button className="btn btn-ghost btn-sm" onClick={loadAlerts}><Icon name="refresh" size={13} /> Refrescar</button>
      </div>

      {evalMsg && <div className="tag tag-green" style={{ display: 'inline-flex', marginBottom: 16 }}><Icon name="check" size={11} /> {evalMsg}</div>}
      {error && <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}><Icon name="warn" size={11} /> {error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* Lista */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div className="card-head">
            <div>
              <div className="card-eyebrow">Activas · por severidad</div>
              <h3 className="card-title">{shown.length} alerta(s)</h3>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {['all', 'critical', 'warning', 'info'].map((s) => (
                <button key={s} className={`btn btn-sm ${sevFilter === s ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setSevFilter(s)}>
                  {s === 'all' ? 'Todas' : s} · {counts[s] || 0}
                </button>
              ))}
            </div>
          </div>
          {shown.length === 0 && (
            <div className="card-body" style={{ textAlign: 'center', padding: '40px 16px', color: 'var(--fg-muted)' }}>
              <div style={{ marginBottom: 8 }}><Icon name="check" size={26} /></div>
              Sin alertas activas. Cargá reglas y "Evaluar ahora".
            </div>
          )}
          {shown.map((a) => <AlertRow key={a.id} a={a} active={a.id === selId} onClick={() => setSelId(a.id)} />)}
        </div>

        {/* Detalle */}
        <AlertDetail
          a={sel} user={user} goTo={goTo}
          onResolve={() => sel && act(sel.id, { status: 'resolved' })}
          onFalse={() => sel && act(sel.id, { status: 'false_alarm' })}
          onAssign={() => sel && act(sel.id, { assigned_to: user?.name || user?.email || 'DBA' })}
        />
      </div>

      <RulesManager
        connectionId={connectionId} rules={rules} wkKeys={wkKeys} busy={busy}
        getToken={getAccessTokenSilently} onChange={loadRules} setError={setError} goTo={goTo}
      />
    </div>
  );
}

function AlertRow({ a, active, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: '14px 20px', borderBottom: '1px solid var(--line)',
        borderLeft: `3px solid ${active ? SEV_COLOR[a.severity] : 'transparent'}`,
        background: active ? 'var(--bg-sunk)' : 'transparent', cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        <span className={`tag ${SEV_TAG[a.severity]}`}>{a.severity}</span>
        {a.auto_remediated && <span className="tag tag-green">auto-remediada</span>}
        <span style={{ flex: 1 }} />
        <span className="metric-mono" style={{ fontSize: 11, color: 'var(--fg-faint)' }}>{fmtTime(a.created_at)}</span>
      </div>
      <div style={{ fontWeight: 500, fontSize: 14, marginBottom: 4 }}>{a.title}</div>
      <div style={{ fontSize: 12.5, color: 'var(--fg-muted)', marginBottom: 8 }}>{a.description}</div>
      <div style={{ display: 'flex', gap: 14, fontSize: 11.5, color: 'var(--fg-faint)', flexWrap: 'wrap' }}>
        <span><Icon name="db" size={11} /> {a.source || '—'}</span>
        {a.suggested_workaround_key && <span><Icon name="play" size={11} /> {a.suggested_workaround_key}</span>}
        <span><Icon name="users" size={11} /> {a.assigned_to || 'Sin asignar'}</span>
      </div>
    </div>
  );
}

function AlertDetail({ a, goTo, onResolve, onFalse, onAssign }) {
  if (!a) {
    return (
      <div className="card" style={{ alignSelf: 'flex-start' }}>
        <div className="card-body" style={{ color: 'var(--fg-muted)', textAlign: 'center', padding: '40px 16px' }}>
          Elegí una alerta para ver el detalle.
        </div>
      </div>
    );
  }
  return (
    <div className="card" style={{ alignSelf: 'flex-start', overflow: 'hidden' }}>
      <div style={{ padding: 4, background: SEV_COLOR[a.severity] }}>
        <div style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10, color: 'var(--cream-100)' }}>
          <Icon name="warn" size={15} />
          <span className="metric-mono" style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>{a.severity}</span>
          <span style={{ flex: 1 }} />
          <span className="metric-mono" style={{ fontSize: 11 }}>{fmtTime(a.created_at)}</span>
        </div>
      </div>
      <div className="card-body">
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, margin: '0 0 8px', fontWeight: 500 }}>{a.title}</h3>
        <p style={{ color: 'var(--fg-muted)', fontSize: 13, margin: '0 0 16px' }}>{a.description}</p>

        <div style={{ background: 'var(--bg-sunk)', border: '1px solid var(--line)', borderRadius: 'var(--radius-sm)', padding: 14, marginBottom: 16, fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.7 }}>
          <div style={{ color: 'var(--fg-faint)', fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>Datos del evento</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px' }}>
            <span style={{ color: 'var(--fg-faint)' }}>fuente</span><span>{a.source || '—'}</span>
            <span style={{ color: 'var(--fg-faint)' }}>métrica</span><span>{a.metric}</span>
            <span style={{ color: 'var(--fg-faint)' }}>valor</span><span style={{ color: SEV_COLOR[a.severity] }}>{a.value}</span>
            <span style={{ color: 'var(--fg-faint)' }}>umbral</span><span>{a.threshold}</span>
            <span style={{ color: 'var(--fg-faint)' }}>estado</span><span>{a.status}{a.auto_remediated ? ' · auto-remediada' : ''}</span>
          </div>
        </div>

        {a.suggested_workaround_key && (
          <>
            <div className="card-eyebrow" style={{ marginBottom: 8 }}>Workaround sugerido</div>
            <div style={{ padding: '10px 14px', border: '1px solid var(--line-strong)', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <Icon name="play" size={14} />
              <div style={{ flex: 1, fontWeight: 500, fontSize: 13 }}>{a.suggested_workaround_key}</div>
            </div>
            <button className="btn btn-primary btn-block" onClick={() => goTo('workarounds')}>
              <Icon name="play" size={14} /> Atender ahora
            </button>
          </>
        )}
        <button className="btn btn-ghost btn-block" style={{ marginTop: 8 }} onClick={onAssign}>Asignarme</button>
        <button className="btn btn-ghost btn-block" style={{ marginTop: 8 }} onClick={onResolve}>Marcar resuelta</button>
        <button className="btn btn-ghost btn-block" style={{ marginTop: 8 }} onClick={onFalse}>Marcar falsa alarma</button>
      </div>
    </div>
  );
}

const EMPTY_RULE = {
  name: '', metric: 'cpu_percent', operator: 'gt', threshold: 85, severity: 'warning',
  database: '', suggested_workaround_key: '', auto_remediate: false, auto_threshold: '',
};

function RulesManager({ connectionId, rules, wkKeys, busy, getToken, onChange, setError, goTo }) {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_RULE);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  async function seed() {
    try {
      const t = await getToken();
      const db = window.prompt('Para la regla de log (por base), ¿qué base? (dejá vacío para omitirla)', '') || '';
      await seedAlertRules(t, connectionId, db);
      onChange();
    } catch (e) { setError(e.message); }
  }

  async function submit() {
    try {
      const t = await getToken();
      await createAlertRule(t, {
        name: form.name, connection_id: connectionId, database: form.database,
        metric: form.metric, operator: form.operator, threshold: Number(form.threshold),
        severity: form.severity, suggested_workaround_key: form.suggested_workaround_key || null,
        auto_remediate: form.auto_remediate,
        auto_threshold: form.auto_threshold === '' ? null : Number(form.auto_threshold),
      });
      setShowForm(false);
      setForm(EMPTY_RULE);
      onChange();
    } catch (e) { setError(e.message); }
  }

  async function toggle(r) {
    try { const t = await getToken(); await updateAlertRule(t, r.id, { enabled: !r.enabled }); onChange(); }
    catch (e) { setError(e.message); }
  }
  async function remove(id) {
    if (!window.confirm('¿Borrar esta regla?')) return;
    try { const t = await getToken(); await deleteAlertRule(t, id); onChange(); }
    catch (e) { setError(e.message); }
  }

  const field = { ...selectStyle, width: '100%', boxSizing: 'border-box' };
  const lbl = { display: 'block', fontSize: 12, color: 'var(--fg-muted)', margin: '0 0 4px' };

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-eyebrow">Umbrales · {connectionId ? `${rules.length} regla(s)` : 'elegí una conexión'}</div>
          <h3 className="card-title">Reglas de alerta</h3>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={seed} disabled={!connectionId || busy}>Cargar recomendadas</button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)} disabled={!connectionId}><Icon name="plus" size={13} /> Nueva regla</button>
        </div>
      </div>

      {showForm && connectionId && (
        <div className="card-body" style={{ background: 'var(--bg-sunk)', borderBottom: '1px solid var(--line)' }}>
          <div className="grid-3" style={{ gap: 12 }}>
            <div><label style={lbl}>Nombre</label><input style={field} value={form.name} onChange={set('name')} placeholder="CPU alta" /></div>
            <div><label style={lbl}>Métrica</label>
              <select style={field} value={form.metric} onChange={set('metric')}>
                {METRICS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </select>
            </div>
            <div><label style={lbl}>Base (solo log_used_pct)</label><input style={field} value={form.database} onChange={set('database')} placeholder="(instancia)" /></div>
            <div><label style={lbl}>Operador</label>
              <select style={field} value={form.operator} onChange={set('operator')}>
                {Object.entries(OP_SYM).map(([k, s]) => <option key={k} value={k}>{s}</option>)}
              </select>
            </div>
            <div><label style={lbl}>Umbral (alerta)</label><input style={field} value={form.threshold} onChange={set('threshold')} /></div>
            <div><label style={lbl}>Severidad</label>
              <select style={field} value={form.severity} onChange={set('severity')}>
                {['info', 'warning', 'critical'].map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div><label style={lbl}>Workaround sugerido</label>
              <select style={field} value={form.suggested_workaround_key} onChange={set('suggested_workaround_key')}>
                <option value="">(ninguno)</option>
                {wkKeys.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
            </div>
            <div><label style={lbl}>Umbral máximo (auto)</label><input style={field} value={form.auto_threshold} onChange={set('auto_threshold')} placeholder="ej. 99" /></div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
              <label style={{ ...lbl, margin: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
                <input type="checkbox" checked={form.auto_remediate} onChange={set('auto_remediate')} /> Auto-remediar al máximo
              </label>
            </div>
          </div>
          <div className="row" style={{ gap: 8, marginTop: 12 }}>
            <button className="btn btn-primary btn-sm" onClick={submit} disabled={!form.name}>Crear regla</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </div>
      )}

      <div style={{ overflow: 'auto' }}>
        <table className="data-table" style={{ fontSize: 12.5 }}>
          <thead>
            <tr><th>Regla</th><th>Métrica</th><th>Condición</th><th>Sev.</th><th>Auto</th><th>Sugerido</th><th>Últ. valor</th><th>On</th><th></th></tr>
          </thead>
          <tbody>
            {!connectionId && <tr><td colSpan={9} style={{ color: 'var(--fg-faint)' }}>Elegí una conexión para ver/crear reglas.</td></tr>}
            {connectionId && rules.length === 0 && <tr><td colSpan={9} style={{ color: 'var(--fg-faint)' }}>Sin reglas. Usá "Cargar recomendadas".</td></tr>}
            {rules.map((r) => (
              <tr key={r.id}>
                <td style={{ fontWeight: 600 }}>{r.name}</td>
                <td className="metric-mono" style={{ fontSize: 11.5 }}>{METRIC_LABEL[r.metric] || r.metric}{r.database ? ` · ${r.database}` : ''}</td>
                <td className="metric-mono">{OP_SYM[r.operator]} {r.threshold}</td>
                <td><span className={`tag ${SEV_TAG[r.severity]}`}>{r.severity}</span></td>
                <td className="metric-mono">{r.auto_remediate ? `≥ ${r.auto_threshold ?? '—'}` : '—'}</td>
                <td className="metric-mono" style={{ fontSize: 11 }}>{r.suggested_workaround_key || '—'}</td>
                <td className="metric-mono">{r.last_value ?? '—'}</td>
                <td>
                  <button className={`tag ${r.enabled ? 'tag-green' : ''}`} style={{ cursor: 'pointer' }} onClick={() => toggle(r)}>{r.enabled ? 'sí' : 'no'}</button>
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
  );
}
