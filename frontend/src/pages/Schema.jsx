import { useState, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import { getConnections, getDatabases, getSchemaOverview, getTables, getTableDetail } from '../api.js';

function fmtKb(kb) {
  if (kb == null) return '—';
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`;
}

function StatCard({ label, value, sub }) {
  return (
    <div className="card">
      <div className="card-body">
        <div className="card-eyebrow">{label}</div>
        <div className="metric-large">{value}</div>
        {sub && <div className="metric-mono" style={{ fontSize: 11, color: 'var(--fg-faint)', marginTop: 6 }}>{sub}</div>}
      </div>
    </div>
  );
}

const selectStyle = {
  padding: '7px 10px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)',
};

export default function SchemaPage({ connectionId, onSelectConnection, goTo }) {
  const { getAccessTokenSilently } = useAuth0();
  const [connections, setConnections] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [database, setDatabase] = useState('');
  const [overview, setOverview] = useState(null);
  const [tables, setTables] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessTokenSilently();
        setConnections(await getConnections(token));
      } catch { /* ignore */ }
    })();
  }, [getAccessTokenSilently]);

  // Al cambiar de instancia: descubrir sus bases y elegir la primera.
  useEffect(() => {
    setDatabase('');
    setDatabases([]);
    setOverview(null);
    setTables([]);
    setSelected(null);
    setDetail(null);
    if (!connectionId) return;
    (async () => {
      setError('');
      try {
        const token = await getAccessTokenSilently();
        const dbs = await getDatabases(token, connectionId);
        setDatabases(dbs);
        if (dbs.length) setDatabase(dbs[0]);
      } catch (e) {
        setError(e.message);
      }
    })();
  }, [connectionId, getAccessTokenSilently]);

  const loadSchema = useCallback(async () => {
    if (!connectionId || !database) {
      setOverview(null);
      setTables([]);
      return;
    }
    setLoading(true);
    setError('');
    setSelected(null);
    setDetail(null);
    try {
      const token = await getAccessTokenSilently();
      const [ov, tbs] = await Promise.all([
        getSchemaOverview(token, connectionId, database),
        getTables(token, connectionId, database),
      ]);
      setOverview(ov);
      setTables(tbs);
    } catch (e) {
      setError(e.message);
      setOverview(null);
      setTables([]);
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently, connectionId, database]);

  useEffect(() => { loadSchema(); }, [loadSchema]);

  async function openTable(t) {
    const id = `${t.schema_name}.${t.table_name}`;
    setSelected(id);
    setDetail(null);
    setDetailLoading(true);
    try {
      const token = await getAccessTokenSilently();
      setDetail(await getTableDetail(token, connectionId, database, t.schema_name, t.table_name));
    } catch (e) {
      setError(e.message);
    } finally {
      setDetailLoading(false);
    }
  }

  const ready = connectionId && database;

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Análisis de BD · Metadata</div>
        <h1 className="page-title">Esquema de la <em>base de datos</em></h1>
        <p className="page-subtitle">Elegí una instancia y una de sus bases para ver tablas, columnas, índices y relaciones.</p>
      </div>

      {/* Selectores: instancia + base */}
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
        {ready && <button className="btn btn-ghost btn-sm" onClick={loadSchema}><Icon name="refresh" size={13} /> Refrescar</button>}
      </div>

      {error && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}>
          <Icon name="warn" size={11} /> {error}
        </div>
      )}

      {connections.length === 0 && (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '48px 16px' }}>
            <div style={{ marginBottom: 10 }}><Icon name="db" size={28} /></div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>No agregaste ninguna conexión</div>
            <div style={{ color: 'var(--fg-muted)', fontSize: 13, marginBottom: 16 }}>Agregá una instancia en el Panel Admin para empezar.</div>
            <button className="btn btn-primary btn-sm" onClick={() => goTo('admin')}><Icon name="plus" size={13} /> Ir al Panel Admin</button>
          </div>
        </div>
      )}

      {connections.length > 0 && !connectionId && (
        <div className="card"><div className="card-body" style={{ color: 'var(--fg-muted)', fontSize: 13 }}>Elegí una instancia en el selector de arriba.</div></div>
      )}

      {connectionId && databases.length === 0 && !error && (
        <div className="card"><div className="card-body" style={{ color: 'var(--fg-muted)', fontSize: 13 }}>La instancia no tiene bases analizables (solo sistema/ReportServer).</div></div>
      )}

      {ready && (
        <>
          <div className="grid-3" style={{ marginBottom: 18 }}>
            <StatCard label="Base de datos" value={overview?.database ?? '—'} sub={overview?.server} />
            <StatCard label="Tablas" value={overview?.table_count ?? '—'} />
            <StatCard label="Tamaño total" value={overview ? fmtKb(overview.total_size_kb) : '—'} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 16, alignItems: 'start' }}>
            <div className="card">
              <div className="card-head">
                <div>
                  <div className="card-eyebrow">Inventario</div>
                  <h3 className="card-title">Tablas</h3>
                </div>
              </div>
              <div style={{ overflow: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Tabla</th>
                      <th style={{ textAlign: 'right' }}>Filas</th>
                      <th style={{ textAlign: 'right' }}>Cols</th>
                      <th style={{ textAlign: 'right' }}>Índices</th>
                      <th style={{ textAlign: 'right' }}>Tamaño</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading && <tr><td colSpan={5} style={{ color: 'var(--fg-faint)' }}>Cargando…</td></tr>}
                    {!loading && tables.length === 0 && (
                      <tr><td colSpan={5} style={{ color: 'var(--fg-faint)' }}>Sin tablas en esta base.</td></tr>
                    )}
                    {tables.map((t) => {
                      const id = `${t.schema_name}.${t.table_name}`;
                      return (
                        <tr key={id} onClick={() => openTable(t)} style={{ cursor: 'pointer', background: selected === id ? 'var(--blue-50)' : undefined }}>
                          <td>
                            <span style={{ fontWeight: 600 }}>{t.table_name}</span>{' '}
                            <span style={{ color: 'var(--fg-faint)', fontSize: 11 }}>{t.schema_name}</span>
                          </td>
                          <td className="metric-mono" style={{ textAlign: 'right' }}>{t.row_count}</td>
                          <td className="metric-mono" style={{ textAlign: 'right' }}>{t.column_count}</td>
                          <td className="metric-mono" style={{ textAlign: 'right' }}>{t.index_count}</td>
                          <td className="metric-mono" style={{ textAlign: 'right' }}>{fmtKb(t.size_kb)}</td>
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
                  <div className="card-eyebrow">Detalle</div>
                  <h3 className="card-title">{selected || 'Seleccioná una tabla'}</h3>
                </div>
                {detail && <span className="tag tag-blue"><Icon name="table" size={10} /> {detail.columns.length} columnas</span>}
              </div>
              <div className="card-body">
                {!selected && <div style={{ color: 'var(--fg-faint)', fontSize: 13 }}>Hacé clic en una tabla para ver columnas, índices y relaciones.</div>}
                {detailLoading && <div style={{ color: 'var(--fg-faint)' }}>Cargando…</div>}
                {detail && !detailLoading && (
                  <>
                    <div className="card-eyebrow" style={{ marginBottom: 8 }}>Columnas</div>
                    <table className="data-table" style={{ marginBottom: 16 }}>
                      <thead><tr><th>Nombre</th><th>Tipo</th><th>Nulo</th><th>PK</th></tr></thead>
                      <tbody>
                        {detail.columns.map((c) => (
                          <tr key={c.name}>
                            <td style={{ fontWeight: 500 }}>{c.name}</td>
                            <td className="metric-mono" style={{ fontSize: 12 }}>{c.data_type}</td>
                            <td>{c.is_nullable ? <span className="tag">NULL</span> : <span className="tag tag-yellow">NOT NULL</span>}</td>
                            <td>{c.is_primary_key ? <span className="tag tag-blue">PK</span> : ''}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    <div className="card-eyebrow" style={{ marginBottom: 8 }}>Índices</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
                      {detail.indexes.length === 0 && <span style={{ color: 'var(--fg-faint)', fontSize: 12 }}>Sin índices.</span>}
                      {detail.indexes.map((i) => (
                        <span key={i.name} className={`tag ${i.is_primary_key ? 'tag-blue' : i.is_unique ? 'tag-green' : ''}`}>
                          {i.name}{i.is_unique && !i.is_primary_key ? ' · UNIQUE' : ''}
                        </span>
                      ))}
                    </div>

                    <div className="card-eyebrow" style={{ marginBottom: 8 }}>Claves foráneas</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {detail.foreign_keys.length === 0 && <span style={{ color: 'var(--fg-faint)', fontSize: 12 }}>Sin claves foráneas.</span>}
                      {detail.foreign_keys.map((f) => (
                        <div key={f.name} style={{ fontSize: 12.5 }}>
                          <Icon name="arrow" size={11} />{' '}
                          <span className="metric-mono">{f.ref_schema}.{f.ref_table}</span>{' '}
                          <span style={{ color: 'var(--fg-faint)' }}>({f.name})</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
