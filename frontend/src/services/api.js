const API_BASE_URL = window.EDGEHEALTH_API_URL || "http://localhost:5000/api";


async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (response.status === 204) {
    return null;
  }

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body.erro || "Erro ao comunicar com a API");
  }

  return body;
}


export const api = {
  login(payload) {
    return request("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  register(payload) {
    return request("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listarDispositivos() {
    return request("/dispositivos");
  },

  criarDispositivo(payload) {
    return request("/dispositivos", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  atualizarDispositivo(id, payload) {
    return request(`/dispositivos/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  excluirDispositivo(id) {
    return request(`/dispositivos/${id}`, {
      method: "DELETE",
    });
  },

  registrarPing(id, payload) {
    return request(`/dispositivos/${id}/ping`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listarMetricas(dispositivoId) {
    return request(`/metricas/dispositivo/${dispositivoId}`);
  },

  criarMetrica(dispositivoId, payload) {
    return request(`/metricas/dispositivo/${dispositivoId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
