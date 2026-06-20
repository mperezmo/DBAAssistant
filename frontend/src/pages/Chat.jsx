import { useState, useRef, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import { sendChat, getConnections, getDatabases } from '../api.js';

function renderContent(text) {
  const parts = String(text).split('```');
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      const nl = part.indexOf('\n');
      const code = (nl >= 0 ? part.slice(nl + 1) : part).replace(/\s+$/, '');
      return (
        <pre key={i} style={{
          margin: '10px 0', padding: 14, background: 'var(--bg-sunk)',
          border: '1px solid var(--line)', borderRadius: 'var(--radius-sm)',
          fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.6,
          color: 'var(--fg)', whiteSpace: 'pre', overflow: 'auto', maxHeight: 320,
        }}>{code}</pre>
      );
    }
    return <span key={i} style={{ whiteSpace: 'pre-wrap' }}>{part}</span>;
  });
}

function UserBubble({ children }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 18 }}>
      <div style={{
        background: 'var(--blue-700)', color: '#fff', padding: '10px 14px',
        borderRadius: '12px 12px 4px 12px', maxWidth: '80%', fontSize: 13.5,
        lineHeight: 1.55, fontWeight: 450, whiteSpace: 'pre-wrap',
      }}>{children}</div>
    </div>
  );
}

function BotBubble({ children }) {
  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: 18 }}>
      <div style={{
        width: 30, height: 30, borderRadius: '50%', background: 'var(--blue-50)',
        border: '1px solid var(--blue-100)', display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontWeight: 700, fontSize: 11, color: 'var(--accent)',
        flexShrink: 0, letterSpacing: '-0.02em',
      }}>AI</div>
      <div style={{ flex: 1, fontSize: 13.5, lineHeight: 1.6, minWidth: 0 }}>{children}</div>
    </div>
  );
}

const SUGGESTIONS = [
  '¿Cómo veo las consultas más lentas en SQL Server?',
  'Generá un índice para acelerar búsquedas por email',
  'Explicá qué es un deadlock',
];

const selectStyle = {
  padding: '6px 9px', borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--line-strong)', background: 'var(--bg-elev)', color: 'var(--fg)', fontSize: 12.5,
};

export default function ChatPage({ connectionId, onSelectConnection }) {
  const { getAccessTokenSilently } = useAuth0();
  const [connections, setConnections] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [database, setDatabase] = useState('');
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const bodyRef = useRef(null);

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
      } catch { /* ignore */ }
    })();
  }, [connectionId, getAccessTokenSilently]);

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setError('');
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text }]);
    setLoading(true);
    try {
      const token = await getAccessTokenSilently();
      const data = await sendChat(token, text, conversationId, connectionId, database);
      setConversationId(data.conversation_id);
      setMessages((m) => [...m, { role: 'assistant', content: data.reply }]);
    } catch (e) {
      setError(e.message || 'Error al enviar el mensaje');
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      send();
    }
  }

  const canSend = !loading && input.trim().length > 0;
  const grounded = connectionId && database;

  return (
    <div className="page" style={{ maxWidth: 1024, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Chat IA · Lenguaje natural</div>
        <h1 className="page-title">Conversación con la <em>base de datos</em></h1>
        <p className="page-subtitle">Escribí en criollo. El asistente te ayuda con T-SQL, rendimiento y administración.</p>
      </div>

      {/* Anclaje opcional a una base: el bot usa su esquema + contexto de negocio */}
      <div className="row" style={{ marginBottom: 16, gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Base (opcional):</span>
        <select value={connectionId || ''} onChange={(e) => onSelectConnection(e.target.value || null)} style={selectStyle}>
          <option value="">— Sin anclar —</option>
          {connections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        {connectionId && (
          <select value={database} onChange={(e) => setDatabase(e.target.value)} style={selectStyle} disabled={databases.length === 0}>
            {databases.length === 0 && <option value="">(sin bases)</option>}
            {databases.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        )}
        {grounded && (
          <span className="tag tag-green" style={{ display: 'inline-flex' }}>
            <Icon name="check" size={10} /> El bot conoce el esquema y el contexto de esta base
          </span>
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-eyebrow">Conversación{conversationId ? ` · ${conversationId.slice(-6)}` : ''}</div>
            <h3 className="card-title">Hilo activo</h3>
          </div>
          <span className="tag tag-blue"><Icon name="db" size={10} /> Anthropic Claude</span>
        </div>

        <div ref={bodyRef} style={{ padding: '20px 22px', minHeight: 280, maxHeight: '52vh', overflow: 'auto' }}>
          {messages.length === 0 && !loading && (
            <div style={{ textAlign: 'center', color: 'var(--fg-faint)', padding: '48px 16px' }}>
              <div style={{ marginBottom: 8 }}><Icon name="chat" size={28} /></div>
              <div style={{ fontSize: 14, color: 'var(--fg-muted)' }}>Empezá la conversación. Por ejemplo:</div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} className="btn btn-ghost btn-sm" onClick={() => setInput(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            m.role === 'user'
              ? <UserBubble key={i}>{m.content}</UserBubble>
              : <BotBubble key={i}>{renderContent(m.content)}</BotBubble>
          ))}

          {loading && (
            <BotBubble><span style={{ color: 'var(--fg-faint)' }}>Pensando…</span></BotBubble>
          )}

          {error && (
            <div className="tag tag-red" style={{ display: 'inline-flex', marginTop: 6 }}>
              <Icon name="warn" size={11} /> {error}
            </div>
          )}
        </div>

        {/* Composer */}
        <div style={{ padding: '14px 18px 16px', borderTop: '1px solid var(--line)', background: 'var(--bg-sunk)' }}>
          <div style={{ border: '1px solid var(--line-strong)', borderRadius: 'var(--radius)', background: 'var(--bg-elev)', padding: '10px 12px' }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Escribí tu consulta… (⌘/Ctrl + ↵ para enviar)"
              style={{ width: '100%', border: 'none', resize: 'none', outline: 'none', background: 'transparent', minHeight: 44, fontSize: 14, lineHeight: 1.5, color: 'var(--fg)' }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
              <span style={{ fontSize: 11.5, color: 'var(--fg-faint)' }}>
                <Icon name="check" size={11} /> {grounded ? 'Anclado a la base seleccionada' : 'Contextualizado para administración de BD'}
              </span>
              <span style={{ flex: 1 }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--fg-faint)' }}>
                <span className="kbd">⌘</span> + <span className="kbd">↵</span>
              </span>
              <button className="btn btn-primary btn-sm" onClick={send} disabled={!canSend} style={{ opacity: canSend ? 1 : 0.5 }}>
                Enviar <Icon name="arrow" size={14} />
              </button>
            </div>
          </div>
          <div style={{ fontSize: 11, color: 'var(--fg-faint)', marginTop: 8, display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <span>● Anthropic Claude · contextualizado</span>
            <span>● Historial en MongoDB</span>
            <span>● Sesión autenticada (Auth0)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
