import { useAuth0 } from '@auth0/auth0-react';
import Logo from './Logo.jsx';

export default function LoginScreen() {
  const { loginWithRedirect } = useAuth0();
  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-brand-stack">
          <Logo size={40} />
          <div className="auth-brand-name">DBA Assistant</div>
          <div className="auth-brand-sub">Database operations</div>
        </div>

        <div className="auth-form">
          <p style={{ textAlign: 'center', color: 'var(--fg-muted)', fontSize: 13, marginBottom: 20, lineHeight: 1.55 }}>
            Accedé con tu cuenta corporativa para conversar con tus bases de datos.
          </p>

          <button className="btn btn-primary btn-block" onClick={() => loginWithRedirect()}>
            Iniciar sesión
          </button>

          <button
            className="btn btn-ghost btn-block"
            style={{ marginTop: 8 }}
            onClick={() => loginWithRedirect({ authorizationParams: { screen_hint: 'signup' } })}
          >
            Crear cuenta
          </button>

          <div className="auth-foot">
            Autenticación segura vía <a href="#" onClick={(e) => e.preventDefault()}>Auth0</a>
          </div>
        </div>
      </div>
    </div>
  );
}
