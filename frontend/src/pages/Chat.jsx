import { useState, useRef, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Icon from '../components/Icon.jsx';
import { sendChat, exportCsv } from '../api.js';

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
    <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
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

function ResultTable({ result, onExport }) {
  const [exporting, setExporting] = useState(false);
  const [err, setErr] = useState('');
  async function go() {
    setExporting(true);
    setErr('');
    try { await onExport(result); } catch (e) { setErr(e.message); } finally { setExporting(false); }
  }
  return (
    <div className="card" style={{ marginBottom: 18, marginLeft: 42 }}>
      <div className="card-head">
        <div>
          <div className="card-eyebrow">{(result.connection_name || result.connection_id)} · {result.database}</div>
          <h3 className="card-title">{result.row_count} fila(s){result.truncated ? ' · TOP 1000' : ''}</h3>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={go} disabled={exporting}>
          <Icon name="download" size={13} /> {exporting ? 'Exportando…' : 'Exportar CSV'}
        </button>
      </div>
      <div style={{ overflow: 'auto', maxHeight: 340 }}>
        <table className="data-table" style={{ fontSize: 12 }}>
          <thead><tr>{result.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>
            {result.rows.length === 0 && <tr><td colSpan={result.columns.length || 1} style={{ color: 'var(--fg-faint)' }}>Sin filas.</td></tr>}
            {result.rows.map((row, i) => (
              <tr key={i}>{row.map((v, j) => <td key={j} className="metric-mono" style={{ fontSize: 11.5 }}>{v === null ? 'NULL' : String(v)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card-foot">
        <span>{result.truncated ? 'Mostrando 1000 filas (hay más). Exportá a CSV para el total.' : 'Resultado completo.'}</span>
        {err && <span style={{ color: 'var(--terracotta)' }}>{err}</span>}
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  '¿Cuántos clientes hay y de qué ciudades?',
  'Mostrame los 10 pedidos más caros',
  'Explicá qué es un deadlock',
];

export default function ChatPage() {
  const { getAccessTokenSilently } = useAuth0();
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const bodyRef = useRef(null);

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
      const data = await sendChat(token, text, conversationId);
      setConversationId(data.conversation_id);
      setMessages((m) => [...m, { role: 'assistant', content: data.reply, result: data.result }]);
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

  async function onExport(result) {
    const token = await getAccessTokenSilently();
    await exportCsv(token, result.connection_id, result.database, result.sql);
  }

  const canSend = !loading && input.trim().length > 0;

  return (
    <div className="page" style={{ maxWidth: 1024, padding: '28px 32px 40px' }}>
      <div className="page-head">
        <div className="page-eyebrow">Chat IA · agente con acceso a tus datos</div>
        <h1 className="page-title">Conversación con la <em>base de datos</em></h1>
        <p className="page-subtitle">Preguntá en criollo. El asistente decide qué base/tablas consultar (según tu Contexto de Negocio), ejecuta la query y te muestra los resultados.</p>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-eyebrow">Conversación{conversationId ? ` · ${conversationId.slice(-6)}` : ''}</div>
            <h3 className="card-title">Hilo activo</h3>
          </div>
          <span className="tag tag-blue"><Icon name="db" size={10} /> Anthropic Claude</span>
        </div>

        <div ref={bodyRef} style={{ padding: '20px 22px', minHeight: 280, maxHeight: '56vh', overflow: 'auto' }}>
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
              : (
                <div key={i}>
                  <BotBubble>{renderContent(m.content)}</BotBubble>
                  {m.result && <ResultTable result={m.result} onExport={onExport} />}
                </div>
              )
          ))}

          {loading && (
            <BotBubble><span style={{ color: 'var(--fg-faint)' }}>Consultando…</span></BotBubble>
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
              placeholder="Preguntá por tus datos… (⌘/Ctrl + ↵ para enviar)"
              style={{ width: '100%', border: 'none', resize: 'none', outline: 'none', background: 'transparent', minHeight: 44, fontSize: 14, lineHeight: 1.5, color: 'var(--fg)' }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
              <span style={{ fontSize: 11.5, color: 'var(--fg-faint)' }}>
                <Icon name="check" size={11} /> El bot elige la base y ejecuta (solo lectura, TOP 1000)
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
            <span>● Anthropic Claude · agente</span>
            <span>● Solo lectura · auditado</span>
            <span>● Exportá el total a CSV</span>
          </div>
        </div>
      </div>
    </div>
  );
}
