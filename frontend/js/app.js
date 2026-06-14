// frontend/js/app.js
// Panel de estado de la infraestructura. API_BASE_URL se define en auth.js.
async function loadStatus() {
  const el = document.getElementById("status");
  el.textContent = "Cargando…";
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    const data = await res.json();
    el.innerHTML = Object.entries(data.services)
      .map(([name, ok]) => `
        <div class="service">
          <span>${name}</span>
          <span class="badge ${ok ? "ok" : "bad"}">${ok ? "OK" : "ERROR"}</span>
        </div>`)
      .join("");
  } catch (e) {
    el.textContent = "No se pudo conectar con la API.";
  }
}

document.getElementById("refresh").addEventListener("click", loadStatus);
