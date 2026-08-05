const statusClass = {
  online: "status-online",
  offline: "status-offline",
  falha: "status-falha",
  manutencao: "status-manutencao",
};


export function renderDashboard(dispositivos) {
  const total = dispositivos.length;
  const online = dispositivos.filter((item) => item.status === "online").length;
  const falha = dispositivos.filter((item) => item.status === "falha").length;
  const offline = dispositivos.filter((item) => item.status === "offline").length;

  const linhas = dispositivos
    .slice(0, 8)
    .map((item) => {
      const classe = statusClass[item.status] || "status-offline";
      return `
        <div class="status-row">
          <div>
            <strong>${item.nome}</strong>
            <div>${item.identificador} ${item.localizacao ? `- ${item.localizacao}` : ""}</div>
          </div>
          <span class="status-pill ${classe}">${item.status}</span>
        </div>
      `;
    })
    .join("");

  return `
    <section class="grid summary-grid">
      <article class="card">
        <p class="metric-label">Dispositivos</p>
        <p class="metric-value">${total}</p>
      </article>
      <article class="card">
        <p class="metric-label">Online</p>
        <p class="metric-value">${online}</p>
      </article>
      <article class="card">
        <p class="metric-label">Falhas</p>
        <p class="metric-value">${falha}</p>
      </article>
      <article class="card">
        <p class="metric-label">Offline</p>
        <p class="metric-value">${offline}</p>
      </article>
    </section>

    <div class="section-title">
      <h2>Status recente</h2>
    </div>
    <section class="card status-list">
      ${linhas || '<p class="empty">Nenhum dispositivo cadastrado.</p>'}
    </section>
  `;
}
