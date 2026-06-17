import { useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Sidebar from './components/Sidebar.jsx';
import Topbar from './components/Topbar.jsx';
import LoginScreen from './components/LoginScreen.jsx';
import ChatPage from './pages/Chat.jsx';
import SchemaPage from './pages/Schema.jsx';
import AdminPage from './pages/Admin.jsx';
import MonitorPage from './pages/Monitor.jsx';
import AuditPage from './pages/Audit.jsx';
import SandboxPage from './pages/Sandbox.jsx';

const PAGES = {
  chat: ChatPage, schema: SchemaPage, admin: AdminPage, monitor: MonitorPage,
  audit: AuditPage, sandbox: SandboxPage,
};

export default function App() {
  const { isLoading, isAuthenticated, error } = useAuth0();
  const [page, setPage] = useState('chat');
  const [env] = useState('DEV');
  const [connectionId, setConnectionId] = useState(() => localStorage.getItem('dba_conn') || null);

  function selectConnection(id) {
    setConnectionId(id);
    if (id) localStorage.setItem('dba_conn', id);
    else localStorage.removeItem('dba_conn');
  }

  if (isLoading) {
    return (
      <div className="auth-screen">
        <div style={{ color: 'var(--fg-muted)' }}>Cargando…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="auth-screen">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <div style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: 8 }}>Error de autenticación</div>
          <div style={{ color: 'var(--fg-muted)', fontSize: 13 }}>{error.message}</div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return <LoginScreen />;

  const Page = PAGES[page] || ChatPage;

  return (
    <div className="app-shell">
      <Sidebar active={page} onNav={setPage} />
      <main className="main">
        <Topbar active={page} env={env} />
        <Page
          env={env}
          connectionId={connectionId}
          onSelectConnection={selectConnection}
          goTo={setPage}
        />
      </main>
    </div>
  );
}
