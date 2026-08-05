import { apiFetch } from "./services/api.js";
import { Dashboard } from "./pages/Dashboard.js";
import { Dispositivos } from "./pages/Dispositivos.js";
import { Login } from "./pages/Login.js";


const app = document.querySelector("#app");


function render() {
  app.innerHTML = `
    <nav>
      <button data-page="login">Login</button>
      <button data-page="dashboard">Dashboard</button>
      <button data-page="dispositivos">Dispositivos</button>
    </nav>
    <main>${Dashboard()}</main>
  `;

  bindNavigation();
}


function bindNavigation() {
  document.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      const page = button.dataset.page;
      const main = document.querySelector("main");

      if (page === "login") {
        main.innerHTML = Login();
      }

      if (page === "dashboard") {
        main.innerHTML = Dashboard();
      }

      if (page === "dispositivos") {
        main.innerHTML = Dispositivos();
        bindDispositivos();
      }
    });
  });
}


function bindDispositivos() {
  const form = document.querySelector("#dispositivo-form");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const dados = Object.fromEntries(new FormData(form).entries());

    await apiFetch("/dispositivos", {
      method: "POST",
      body: JSON.stringify(dados),
    });

    form.reset();
  });
}


render();
