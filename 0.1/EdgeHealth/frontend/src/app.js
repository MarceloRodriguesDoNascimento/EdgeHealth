import { apiFetch } from "./services/api.js";
import { Dashboard } from "./pages/Dashboard.js";
import { Dispositivos } from "./pages/Dispositivos.js";
import { Empresas } from "./pages/Empresas.js";
import { Login } from "./pages/Login.js";

const app = document.querySelector("#app");

function render() {
  app.innerHTML = `
    <nav>
      <button data-page="login">Login</button>
      <button data-page="dashboard">Dashboard</button>
      <button data-page="dispositivos">Dispositivos</button>
      <button data-page="empresas">Empresas</button>
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

      if (page === "empresas") {
        main.innerHTML = Empresas();
        bindEmpresas();
      }
    });
  });
}

async function carregarDispositivos() {
  const lista = document.querySelector("#dispositivos-lista");
  const dados = await apiFetch("/dispositivos");

  lista.innerHTML = dados
    .map(
      (item) => `
      <li>
        <strong>${item.nome}</strong> (${item.ip}) - ${item.tipo || "sem tipo"}
        <button data-action="editar" data-id="${item.id}">Editar</button>
        <button data-action="deletar" data-id="${item.id}">Excluir</button>
      </li>
    `
    )
    .join("");
}

function bindDispositivos() {
  const form = document.querySelector("#dispositivo-form");
  const listContainer = document.querySelector("#dispositivos-lista");
  let editDispositivoId = null;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const dados = Object.fromEntries(new FormData(form).entries());

    if (editDispositivoId) {
      await apiFetch(`/dispositivos/${editDispositivoId}`, {
        method: "PUT",
        body: JSON.stringify(dados),
      });
      editDispositivoId = null;
      form.querySelector("button[type=submit]").textContent = "Cadastrar";
    } else {
      await apiFetch("/dispositivos", {
        method: "POST",
        body: JSON.stringify(dados),
      });
    }

    form.reset();
    carregarDispositivos();
  });

  listContainer.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) {
      return;
    }

    const id = button.dataset.id;
    const action = button.dataset.action;

    if (action === "deletar") {
      await apiFetch(`/dispositivos/${id}`, { method: "DELETE" });
      carregarDispositivos();
      return;
    }

    if (action === "editar") {
      const dispositivo = await apiFetch(`/dispositivos/${id}`);
      form.nome.value = dispositivo.nome || "";
      form.ip.value = dispositivo.ip || "";
      form.tipo.value = dispositivo.tipo || "";
      form.setor.value = dispositivo.setor || "";
      editDispositivoId = id;
      form.querySelector("button[type=submit]").textContent = "Atualizar";
    }
  });

  carregarDispositivos();
}

async function carregarEmpresas() {
  const lista = document.querySelector("#empresas-lista");
  const dados = await apiFetch("/empresas");

  lista.innerHTML = dados
    .map(
      (item) => `
      <li>
        <strong>${item.nome_fantasia}</strong> - ${item.cnpj}
        <button data-action="editar" data-id="${item.id}">Editar</button>
        <button data-action="deletar" data-id="${item.id}">Excluir</button>
      </li>
    `
    )
    .join("");
}

function bindEmpresas() {
  const form = document.querySelector("#empresa-form");
  const listContainer = document.querySelector("#empresas-lista");
  let editEmpresaId = null;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const dados = Object.fromEntries(new FormData(form).entries());

    if (editEmpresaId) {
      await apiFetch(`/empresas/${editEmpresaId}`, {
        method: "PUT",
        body: JSON.stringify(dados),
      });
      editEmpresaId = null;
      form.querySelector("button[type=submit]").textContent = "Cadastrar";
    } else {
      await apiFetch("/empresas", {
        method: "POST",
        body: JSON.stringify(dados),
      });
    }

    form.reset();
    carregarEmpresas();
  });

  listContainer.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) {
      return;
    }

    const id = button.dataset.id;
    const action = button.dataset.action;

    if (action === "deletar") {
      await apiFetch(`/empresas/${id}`, { method: "DELETE" });
      carregarEmpresas();
      return;
    }

    if (action === "editar") {
      const empresa = await apiFetch(`/empresas/${id}`);
      form.nome_fantasia.value = empresa.nome_fantasia || "";
      form.cnpj.value = empresa.cnpj || "";
      editEmpresaId = id;
      form.querySelector("button[type=submit]").textContent = "Atualizar";
    }
  });

  carregarEmpresas();
}

render();
