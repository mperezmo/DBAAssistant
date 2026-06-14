const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return res.json();
}

function authGet(token, path) {
  return request(path, { headers: { Authorization: `Bearer ${token}` } });
}

// ── Chat (Sprint 3) ──
export function sendChat(token, message, conversationId) {
  return request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message, conversation_id: conversationId || null }),
  });
}

// ── Esquema / metadata (Sprint 4) ──
export const getSchemaOverview = (token) => authGet(token, '/schema/overview');
export const getTables = (token) => authGet(token, '/schema/tables');
export const getTableDetail = (token, schema, table) =>
  authGet(token, `/schema/tables/${schema}/${table}`);
