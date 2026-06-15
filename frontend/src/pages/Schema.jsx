import { useState, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import { getSchemaOverview, getTables, getTableDetail } from '../api.js';

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
        {sub && (
          <div className="metric-mono" style={{ fontSize: 11, color: 'var(--fg-faint)', marginTop: 6 }}>
            {sub}
          </div>
        )}
      </div>
    </div>
  );
}

export default function SchemaPage() {
  const { getAccessTokenSilently } = useAuth0();
  const [overview, setOverview] = useState(null);
  const [tables, setTables] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const token = await getAccessTokenSilently();
      const [ov, tbs] = await Promise.all([getSchemaOverview(token), getTables(token)]);
      setOverview(ov);
      setTables(tbs);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => { load(); }, [load]);

  async function openTable(t) {
    const id = `${t.schema_name}.${t.table_name}`;
    setSelected(id);
    setDetail(null);
    setDetailLoading(true);
    try {
      const token = await getAccessTokenSilently();
      setDetail(await getTableDetail(token, t.schema_name, t.table_name));
    } catch (e) {
      setError(e.message);
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="page" style={{ maxWidth: 1280, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Análisis de BD · Metadata</div>
        <h1 className="page-title">Esquema de la <em>base de datos</em></h1>
        <p className="page-subtitle">
          Tablas, columnas, índices y relaciones leídas en vivo desde SQL Server.
        </p>
      </div>

      {error && (
        <div className="tag tag-red" style={{ display: 'inline-flex', marginBottom: 16 }}>
          <Icon name="warn" size={11} /> {error}
        </div>
      )}

      <div className="grid-3" style={{ marginBottom: 18 }}>
        <StatCard label="Base de datos" value={overview?.database ?? '—'} sub={overview?.server} />
        <StatCard label="Tablas" value={overview?.table_count ?? '—'} />
        <StatCard label="Tamaño total" value={overview ? fmtKb(overview.total_size_kb) : '—'} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 16, alignItems: 'start' }}>
        {/* Tablas */}
        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-eyebrow">Inventario</div>
              <h3 className="card-title">Tablas</h3>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={load}>
              <Icon name="refresh" size={13} /> Refrescar
            </button>
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
                    <tr
                      key={id}
                      onClick={() => openTable(t)}
                      style={{ cursor: 'pointer', background: selected === id ? 'var(--blue-50)' : undefined }}
                    >
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

        {/* Detalle */}
        <div className="card">
          <div className="card-head">
            <div>
              <div className="card-eyebrow">Detalle</div>
              <h3 className="card-title">{selected || 'Seleccioná una tabla'}</h3>
            </div>
            {detail && (
              <span className="tag tag-blue"><Icon name="table" size={10} /> {detail.columns.length} columnas</span>
            )}
          </div>
          <div className="card-body">
            {!selected && (
              <div style={{ color: 'var(--fg-faint)', fontSize: 13 }}>
                Hacé clic en una tabla para ver columnas, índices y relaciones.
              </div>
            )}
            {detailLoading && <div style={{ color: 'var(--fg-faint)' }}>Cargando…</div>}
            {detail && !detailLoading && (
              <>
                <div className="card-eyebrow" style={{ marginBottom: 8 }}>Columnas</div>
                <table className="data-table" style={{ marginBottom: 16 }}>
                  <thead>
                    <tr><th>Nombre</th><th>Tipo</th><th>Nulo</th><th>PK</th></tr>
                  </thead>
                  <tbody>
                    {detail.columns.map((c) => (
                      <tr key={c.name}>
                        <td style={{ fontWeight: 500 }}>{c.name}</td>
                        <td className="metric-mono" style={{ fontSize: 12 }}>{c.data_type}</td>
                        <td>{c.is_nullable
                          ? <span className="tag">NULL</span>
                          : <span className="tag tag-yellow">NOT NULL</span>}</td>
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
    </div>
  );
}
