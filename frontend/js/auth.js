// frontend/js/auth.js
// Manejo de autenticación (modo local JWT) y alternancia de vistas.
const API_BASE_URL = "http://localhost:8000";
const TOKEN_KEY = "dba_token";

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
function clearToken() { localStorage.removeItem(TOKEN_KEY); }

function authHeaders() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function login(username, password) {
  // OAuth2PasswordRequestForm espera form-urlencoded
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Error de autenticación");
  }
  const data = await res.json();
  setToken(data.access_token);
}

async function fetchMe() {
  const res = await fetch(`${API_BASE_URL}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Token inválido o expirado");
  return res.json();
}

function showLogin() {
  document.getElementById("login-view").style.display = "block";
  document.getElementById("app-view").style.display = "none";
}

function showApp(user) {
  document.getElementById("login-view").style.display = "none";
  document.getElementById("app-view").style.display = "block";
  const roles = user.roles && user.roles.length ? user.roles.join(", ") : "sin rol";
  document.getElementById("user-info").textContent =
    `👤 ${user.full_name || user.username} (${roles})`;
  if (typeof loadStatus === "function") loadStatus();
}

function logout() {
  clearToken();
  showLogin();
}

async function initAuth() {
  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("login-error");
    errEl.textContent = "";
    try {
      await login(
        document.getElementById("username").value,
        document.getElementById("password").value
      );
      showApp(await fetchMe());
    } catch (err) {
      errEl.textContent = err.message;
    }
  });
  document.getElementById("logout-btn").addEventListener("click", logout);

  // Si ya hay un token guardado y sigue siendo válido, saltamos el login.
  if (getToken()) {
    try {
      showApp(await fetchMe());
      return;
    } catch {
      clearToken();
    }
  }
  showLogin();
}

window.addEventListener("DOMContentLoaded", initAuth);
