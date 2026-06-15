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

// ── Conexiones (Sprint 4) ──
export const getConnections = (token) => authGet(token, '/connections');
export const createConnection = (token, body) => authSend(token, 'POST', '/connections', body);
export const testConnection = (token, body) => authSend(token, 'POST', '/connections/test', body);
export const deleteConnection = (token, id) => authSend(token, 'DELETE', `/connections/${id}`);

// ── Esquema por conexión (Sprint 4) ──
export const getSchemaOverview = (token, conn) => authGet(token, `/schema/${conn}/overview`);
export const getTables = (token, conn) => authGet(token, `/schema/${conn}/tables`);
export const getTableDetail = (token, conn, schema, table) =>
  authGet(token, `/schema/${conn}/tables/${schema}/${table}`);

// ── Performance por conexión (Sprint 4) ──
export const getPerfMetrics = (token, conn) => authGet(token, `/performance/${conn}/metrics`);
export const getActiveSessions = (token, conn) => authGet(token, `/performance/${conn}/sessions`);
export const getTopQueries = (token, conn) => authGet(token, `/performance/${conn}/top-queries`);
