import { useState, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import {
  getConnections, getDatabases, getTables, getTableDetail,
  getDbContext, putDbContext, getTableContexts, getTableContext, putTableContext,
} from '../api.js';

const selectStyle = {
  padding: '7px 10px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)',
};
const inputStyle = {
  width: '100%', padding: '8px 10px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)',
};
const areaStyle = { ...inputStyle, fontFamily: 'var(--font-mono)', fontSize: 12.5, lineHeight: 1.6, resize: 'vertical' };

const textToRules = (t) => t.split('\n').map((x) => x.trim()).filter(Boolean);
const textToGlossary = (t) => t.split('\n').filter((l) => l.trim()).map((line) => {
  const i = line.indexOf('=');
  return i >= 0 ? { term: line.slice(0, i).trim(), definition: line.slice(i + 1).trim() } : { term: line.trim(), definition: '' };
});

export default function ContextPage({ connectionId, onSelectConnection, goTo }) {
  const { getAccessTokenSilently } = useAuth0();
  const [connections, setConnections] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [database, setDatabase] = useState('');
  const [desc, setDesc] = useState('');
  const [rulesText, setRulesText] = useState('');
  const [glossaryText, setGlossaryText] = useState('');
  const [tables, setTables] = useState([]);
  const [tableCtx, setTableCtx] = useState({});
  const [selected, setSelected] = useState(null);
  const [tform, setTform] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');

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

  const loadAll = useCallback(async () => {
    if (!connectionId || !database) return;
    setError('');
    setSaved('');
    setSelected(null);
    setTform(null);
    try {
      const t = await getAccessTokenSilently();
      const [dbc, tbs, tcs] = await Promise.all([
        getDbContext(t, connectionId, database),
        getTables(t, connectionId, database),
        getTableContexts(t, connectionId, database),
      ]);
      setDesc(dbc.description || '');
      setRulesText((dbc.rules || []).join('\n'));
      setGlossaryText((dbc.glossary || []).map((g) => `${g.term} = ${g.definition}`).join('\n'));
      setTables(tbs);
      const map = {};
      tcs.forEach((e2) => { map[`${e2.schema_name}.${e2.table_name}`] = e2; });
      setTableCtx(map);
    } catch (e) { setError(e.message); }
  }, [connectionId, database, getAccessTokenSilently]);

  useEffect(() => { loadAll(); }, [loadAll]);

  async function saveDb() {
    setBusy(true); setError(''); setSaved('');
    try {
      const t = await getAccessTokenSilently();
      await putDbContext(t, connectionId, database, {
        description: desc, rules: textToRules(rulesText), glossary: textToGlossary(glossaryText),
      });
      setSaved('Contexto de la base guardado.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  async function openTable(tb) {
    const id = `${tb.schema_name}.${tb.table_name}`;
    setSelected(id);
    try {
      const t = await getAccessTokenSilently();
      const [ctx, detail] = await Promise.all([
        getTableContext(t, connectionId, database, tb.schema_name, tb.table_name),
        getTableDetail(t, connectionId, database, tb.schema_name, tb.table_name),
      ]);
      setTform({
        schema_name: tb.schema_name, table_name: tb.table_name, ...ctx,
        tagsText: (ctx.tags || []).join(', '),
        columns: (detail.columns || []).map((c) => c.name),
      });
    } catch (e) { setError(e.message); }
  }

  function toggleSensitiveCol(name) {
    const set = new Set((tform.sensitive_columns || '').split(',').map((s) => s.trim()).filter(Boolean));
    if (set.has(name)) set.delete(name); else set.add(name);
    upd('sensitive_columns', Array.from(set).join(', '));
  }

  async function saveTable() {
    setBusy(true); setError(''); setSaved('');
    try {
      const t = await getAccessTokenSilently();
      const body = {
        business_name: tform.business_name, description: tform.description,
        tags: tform.tagsText.split(',').map((x) => x.trim()).filter(Boolean),
        sensitive: tform.sensitive, sensitive_columns: tform.sensitive_columns, restriction: tform.restriction,
      };
      await putTableContext(t, connectionId, database, tform.schema_name, tform.table_name, body);
      setTableCtx((prev) => ({ ...prev, [`${tform.schema_name}.${tform.table_name}`]: { schema_name: tform.schema_name, table_name: tform.table_name, ...body } }));
      setSaved('Contexto de tabla guardado.');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  const upd = (k, v) => setTform((f) => ({ ...f, [k]: v }));
  const ready = connectionId && database;

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Contexto de negocio · memoria del sistema</div>
        <h1 className="page-title">Tablas, glosario, <em>reglas</em>.</h1>
        <p className="page-subtitle">El motor IA usa este contexto para generar SQL con precisión sobre el dominio del negocio.</p>
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

      {error && <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}><Icon name="warn" size={11} /> {error}</div>}
      {saved && <div className="tag tag-green" style={{ display: 'inline-flex', marginBottom: 16 }}><Icon name="check" size={11} /> {saved}</div>}

      {connections.length === 0 && (
        <div className="card"><div className="card-body" style={{ textAlign: 'center', padding: '48px 16px' }}>
          <div style={{ marginBottom: 10 }}><Icon name="book" size={28} /></div>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>No agregaste ninguna conexión</div>
          <button className="btn btn-primary btn-sm" onClick={() => goTo('admin')}><Icon name="plus" size={13} /> Ir al Panel Admin</button>
        </div></div>
      )}

      {ready && (
        <>
          {/* Contexto de la base */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-head">
              <div>
                <div className="card-eyebrow">Glosario y reglas · alimenta la IA</div>
                <h3 className="card-title">Contexto de la base</h3>
              </div>
              <button className="btn btn-primary btn-sm" onClick={saveDb} disabled={busy}>Guardar</button>
            </div>
            <div className="card-body" style={{ display: 'grid', gap: 14 }}>
              <div className="field"><label>Descripción</label>
                <textarea value={desc} onChange={(e) => setDesc(e.target.value)} style={{ ...areaStyle, minHeight: 56, fontFamily: 'inherit' }} placeholder="¿Qué representa esta base en el negocio?" /></div>
              <div className="field"><label>Reglas operativas (una por línea)</label>
                <textarea value={rulesText} onChange={(e) => setRulesText(e.target.value)} style={{ ...areaStyle, minHeight: 80 }} placeholder={'No exponer sueldos sin enmascarar\nTodas las fechas en UTC'} /></div>
              <div className="field">
                <label>Glosario del negocio</label>
                <div style={{ fontSize: 11.5, color: 'var(--fg-faint)', marginBottom: 6, lineHeight: 1.5 }}>
                  Definí términos propios del negocio y qué significan en los datos, para que la IA los
                  entienda al generar SQL. Escribí <strong>uno por línea</strong> con el formato{' '}
                  <span className="metric-mono">término = qué significa o cómo se calcula</span>.
                </div>
                <textarea value={glossaryText} onChange={(e) => setGlossaryText(e.target.value)} style={{ ...areaStyle, minHeight: 90 }}
                  placeholder={'cliente activo = clientes con estado=1 que compraron en los últimos 6 meses\nfactura vencida = facturas con estado pendiente y fecha de vencimiento anterior a hoy'} />
              </div>
            </div>
          </div>

          {/* Contexto por tabla */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 16, alignItems: 'start' }}>
            <div className="card">
              <div className="card-head"><div><div className="card-eyebrow">Mapeo de tablas</div><h3 className="card-title">Tablas</h3></div></div>
              <div style={{ overflow: 'auto' }}>
                <table className="data-table">
                  <thead><tr><th>Tabla</th><th>Alias de negocio</th><th>Sensible</th></tr></thead>
                  <tbody>
                    {tables.length === 0 && <tr><td colSpan={3} style={{ color: 'var(--fg-faint)' }}>Sin tablas.</td></tr>}
                    {tables.map((tb) => {
                      const id = `${tb.schema_name}.${tb.table_name}`;
                      const ctx = tableCtx[id];
                      return (
                        <tr key={id} onClick={() => openTable(tb)} style={{ cursor: 'pointer', background: selected === id ? 'var(--blue-50)' : undefined }}>
                          <td><span style={{ fontWeight: 600 }}>{tb.table_name}</span> <span style={{ color: 'var(--fg-faint)', fontSize: 11 }}>{tb.schema_name}</span></td>
                          <td style={{ fontSize: 12 }}>{ctx?.business_name || <span style={{ color: 'var(--fg-faint)' }}>—</span>}</td>
                          <td>{ctx?.sensitive ? <span className="tag tag-yellow" style={{ padding: '1px 6px', fontSize: 9.5 }}>{ctx.restriction || 'sensible'}</span> : ''}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-head"><div><div className="card-eyebrow">Detalle</div><h3 className="card-title">{selected || 'Elegí una tabla'}</h3></div></div>
              <div className="card-body">
                {!tform && <div style={{ color: 'var(--fg-faint)', fontSize: 13 }}>Hacé clic en una tabla para describir su significado de negocio.</div>}
                {tform && (
                  <div style={{ display: 'grid', gap: 12 }}>
                    <div className="field"><label>Nombre de negocio</label><input style={inputStyle} value={tform.business_name} onChange={(e) => upd('business_name', e.target.value)} placeholder="Clientes" /></div>
                    <div className="field"><label>Descripción</label><textarea style={{ ...areaStyle, minHeight: 56, fontFamily: 'inherit' }} value={tform.description} onChange={(e) => upd('description', e.target.value)} /></div>
                    <div className="field"><label>Tags (separados por coma)</label><input style={inputStyle} value={tform.tagsText} onChange={(e) => upd('tagsText', e.target.value)} placeholder="core, ventas" /></div>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                      <input type="checkbox" checked={tform.sensitive} onChange={(e) => upd('sensitive', e.target.checked)} /> Tabla sensible
                    </label>
                    {tform.sensitive && (() => {
                      const selectedSensitive = new Set((tform.sensitive_columns || '').split(',').map((s) => s.trim()).filter(Boolean));
                      return (
                        <>
                          <div className="field">
                            <label>Columnas sensibles</label>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 14px', border: '1px solid var(--line)', borderRadius: 'var(--radius-sm)', padding: '10px 12px', background: 'var(--bg-sunk)' }}>
                              {(tform.columns || []).length === 0 && <span style={{ color: 'var(--fg-faint)', fontSize: 12 }}>Sin columnas.</span>}
                              {(tform.columns || []).map((name) => (
                                <label key={name} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12.5, cursor: 'pointer' }}>
                                  <input type="checkbox" checked={selectedSensitive.has(name)} onChange={() => toggleSensitiveCol(name)} />
                                  <span className="metric-mono">{name}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                          <div className="field">
                            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                              Restricción
                              <span
                                title="Cómo se controla el acceso a esta tabla sensible: p. ej. enmascaramiento de datos, doble confirmación antes de consultar, o restricción por rol. Es una nota para el equipo y para la IA."
                                style={{ display: 'inline-flex', color: 'var(--fg-faint)', cursor: 'help' }}
                              >
                                <Icon name="info" size={13} />
                              </span>
                            </label>
                            <input style={inputStyle} value={tform.restriction} onChange={(e) => upd('restriction', e.target.value)} placeholder="enmascaramiento / doble confirmación / por rol" />
                          </div>
                        </>
                      );
                    })()}
                    <button className="btn btn-primary btn-sm" onClick={saveTable} disabled={busy}>Guardar tabla</button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
