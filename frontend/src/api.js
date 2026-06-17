const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (res.status === 204) return null;
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return res.json();
}

function authGet(token, path) {
  return request(path, { headers: { Authorization: `Bearer ${token}` } });
}

function authSend(token, method, path, body) {
  return request(path, {
    method,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: body ? JSON.stringify(body) : undefined,
  });
}

// ── Health (público) ──
export const getHealth = () => request('/health');

// ── Chat (Sprint 3) ──
export function sendChat(token, message, conversationId) {
  return authSend(token, 'POST', '/chat', { message, conversation_id: conversationId || null });
}

// ── Conexiones = instancias (Sprint 4) ──
export const getConnections = (token) => authGet(token, '/connections');
export const createConnection = (token, body) => authSend(token, 'POST', '/connections', body);
export const testConnection = (token, body) => authSend(token, 'POST', '/connections/test', body);
export const deleteConnection = (token, id) => authSend(token, 'DELETE', `/connections/${id}`);
const _r = (refresh) => (refresh ? '?refresh=true' : '');
export const getDatabases = (token, conn, refresh) => authGet(token, `/connections/${conn}/databases${_r(refresh)}`);

// ── Esquema por conexión + base (Sprint 4) · caché Redis (Sprint 6) ──
const e = encodeURIComponent;
export const getSchemaOverview = (token, conn, db, refresh) => authGet(token, `/schema/${conn}/${e(db)}/overview${_r(refresh)}`);
export const getTables = (token, conn, db, refresh) => authGet(token, `/schema/${conn}/${e(db)}/tables${_r(refresh)}`);
export const getTableDetail = (token, conn, db, schema, table) =>
  authGet(token, `/schema/${conn}/${e(db)}/tables/${e(schema)}/${e(table)}`);

// ── Caché (Sprint 6) ──
export const getCacheStats = (token) => authGet(token, '/cache/stats');
export const clearCache = (token) => authSend(token, 'POST', '/cache/clear');

// ── Performance por conexión (Sprint 4) ──
export const getPerfMetrics = (token, conn) => authGet(token, `/performance/${conn}/metrics`);
export const getActiveSessions = (token, conn) => authGet(token, `/performance/${conn}/sessions`);
export const getTopQueries = (token, conn) => authGet(token, `/performance/${conn}/top-queries`);

// ── Auditoría (Sprint 4) ──
export const getAudit = (token) => authGet(token, '/audit?limit=200');

// ── SQL: generación y ejecución (Sprint 5) ──
export const generateSql = (token, body) => authSend(token, 'POST', '/sql/generate', body);
export const executeSql = (token, body) => authSend(token, 'POST', '/sql/execute', body);
export const getQueryHistory = (token) => authGet(token, '/sql/history?limit=50');
