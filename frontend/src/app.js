import { renderDashboard } from "./pages/Dashboard.js";
import { renderDispositivos } from "./pages/Dispositivos.js";
import { renderLogin } from "./pages/Login.js";
import { api } from "./services/api.js";


const root = document.querySelector("#app");

const state = {
  view: "dashboard",
  usuario: null,
  token: null,
  dispositivos: [],
  loading: false,
};


function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}


function setError(id, error) {
  const target = document.querySelector(id);
  if (!target) {
    return;
  }

  target.textContent = error.message || String(error);
  target.hidden = false;
}


async function carregarDispositivos() {
  state.loading = true;
  render();

  try {
    state.dispositivos = await api.listarDispositivos();
  } catch (error) {
    state.dispositivos = [];
  } finally {
    state.loading = false;
    render();
  }
}


function renderShell(content) {
  const usuario = state.usuario?.nome || "Operador";

  root.innerHTML = `
    <div class="shell">
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark">EH</div>
          <div>
            <h1>EdgeHealth</h1>
            <p>${usuario}</p>
          </div>
        </div>
        <nav class="nav">
          <button type="button" data-view="dashboard" class="${state.view === "dashboard" ? "active" : ""}">Dashboard</button>
          <button type="button" data-view="dispositivos" class="${state.view === "dispositivos" ? "active" : ""}">Dispositivos</button>
          <button type="button" data-action="logout">Sair</button>
        </nav>
      </header>
      ${state.loading ? '<p class="notice">Carregando dados da API...</p>' : ""}
      ${content}
    </div>
  `;
}


function render() {
  if (!state.usuario) {
    root.innerHTML = renderLogin();
    bindLogin();
    return;
  }

  const content =
    state.view === "dispositivos"
      ? renderDispositivos(state.dispositivos)
      : renderDashboard(state.dispositivos);

  renderShell(content);
  bindShell();

  if (state.view === "dispositivos") {
    bindDispositivos();
  }
}


function bindLogin() {
  const loginTab = document.querySelector("#login-tab");
  const registerTab = document.querySelector("#register-tab");
  const loginForm = document.querySelector("#login-form");
  const registerForm = document.querySelector("#register-form");

  loginTab.addEventListener("click", () => {
    loginTab.classList.add("active");
    registerTab.classList.remove("active");
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");
  });

  registerTab.addEventListener("click", () => {
    registerTab.classList.add("active");
    loginTab.classList.remove("active");
    registerForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const result = await api.login(formData(loginForm));
      state.usuario = result.usuario;
      state.token = result.token;
      await carregarDispositivos();
    } catch (error) {
      setError("#login-error", error);
    }
  });

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const result = await api.register(formData(registerForm));
      state.usuario = result.usuario;
      await carregarDispositivos();
    } catch (error) {
      setError("#register-error", error);
    }
  });
}


function bindShell() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      render();
    });
  });

  document.querySelector('[data-action="logout"]').addEventListener("click", () => {
    state.usuario = null;
    state.token = null;
    state.dispositivos = [];
    render();
  });
}


function bindDispositivos() {
  const form = document.querySelector("#device-form");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      await api.criarDispositivo(formData(form));
      form.reset();
      await carregarDispositivos();
    } catch (error) {
      setError("#device-error", error);
    }
  });

  document.querySelectorAll("[data-device-id]").forEach((row) => {
    row.addEventListener("click", async (event) => {
      const action = event.target.dataset.action;
      if (!action) {
        return;
      }

      const id = row.dataset.deviceId;

      try {
        if (action === "delete") {
          await api.excluirDispositivo(id);
        }

        if (action === "save") {
          await api.atualizarDispositivo(id, formDataFromRow(row));
        }

        if (action === "ping") {
          await api.registrarPing(id, {
            status: row.querySelector('[name="status"]').value,
            metricas: {
              latencia_ms: Math.round(20 + Math.random() * 180),
              cpu_percent: Math.round(10 + Math.random() * 70),
              memoria_percent: Math.round(20 + Math.random() * 60),
            },
          });
        }

        await carregarDispositivos();
      } catch (error) {
        setError("#device-error", error);
      }
    });
  });
}


function formDataFromRow(row) {
  const payload = {};

  row.querySelectorAll("input, select").forEach((field) => {
    payload[field.name] = field.value;
  });

  return payload;
}


render();
