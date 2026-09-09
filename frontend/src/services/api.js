export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}
export async function apiFetch(path, options = {}) {
  const csrf = document.cookie.split('; ').find(x => x.startsWith('edgehealth_csrf='))?.split('=').slice(1).join('=');
  let response;
  try {
    response = await fetch(`/api${path}`, {
      credentials: 'same-origin', ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(csrf ? { 'X-CSRF-Token': decodeURIComponent(csrf) } : {}), ...options.headers }
    });
  } catch {
    throw new ApiError('Não foi possível conectar ao servidor. Verifique a conexão e tente novamente.', 0);
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    if (response.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('session-expired'));
    throw new ApiError(error.erro || 'Não foi possível concluir a operação.', response.status);
  }
  if (response.status === 204) return null;
  if (options.download) return response.blob();
  return response.json();
}
export const json = data => JSON.stringify(data);
