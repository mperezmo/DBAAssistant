import { useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import Sidebar from './components/Sidebar.jsx';
import Topbar from './components/Topbar.jsx';
import LoginScreen from './components/LoginScreen.jsx';
import ChatPage from './pages/Chat.jsx';

export default function App() {
  const { isLoading, isAuthenticated, error } = useAuth0();
  const [page, setPage] = useState('chat');
  const [env] = useState('DEV');

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

  return (
    <div className="app-shell">
      <Sidebar active={page} onNav={setPage} />
      <main className="main">
        <Topbar active={page} env={env} />
        <ChatPage env={env} />
      </main>
    </div>
  );
}
