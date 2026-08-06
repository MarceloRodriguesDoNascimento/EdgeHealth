const API_URL = "http://localhost:5000/api";


export async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error("Erro ao consumir a API");
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
