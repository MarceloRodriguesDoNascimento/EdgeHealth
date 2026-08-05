const statuses = ["online", "offline", "falha", "manutencao"];


function statusOptions(statusAtual) {
  return statuses
    .map((status) => {
      const selected = status === statusAtual ? "selected" : "";
      return `<option value="${status}" ${selected}>${status}</option>`;
    })
    .join("");
}


export function renderDispositivos(dispositivos) {
  const rows = dispositivos
    .map(
      (item) => `
        <tr data-device-id="${item.id}">
          <td><input class="row-input" name="nome" value="${item.nome}" /></td>
          <td><input class="row-input" name="identificador" value="${item.identificador}" /></td>
          <td><input class="row-input" name="tipo" value="${item.tipo}" /></td>
          <td><input class="row-input" name="localizacao" value="${item.localizacao || ""}" /></td>
          <td>
            <select class="row-input" name="status">
              ${statusOptions(item.status)}
            </select>
          </td>
          <td class="actions">
            <button class="ghost-button" data-action="ping" type="button">Ping</button>
            <button class="primary-button" data-action="save" type="button">Salvar</button>
            <button class="danger-button" data-action="delete" type="button">Excluir</button>
          </td>
        </tr>
      `,
    )
    .join("");

  return `
    <section class="card">
      <form class="device-form" id="device-form">
        <label>
          Nome
          <input name="nome" required />
        </label>
        <label>
          Identificador
          <input name="identificador" required />
        </label>
        <label>
          Tipo
          <input name="tipo" value="sensor" required />
        </label>
        <label>
          Localizacao
          <input name="localizacao" />
        </label>
        <label>
          Status
          <select name="status">
            ${statusOptions("offline")}
          </select>
        </label>
        <button class="primary-button" type="submit">Adicionar</button>
      </form>
    </section>

    <div class="section-title">
      <h2>Dispositivos</h2>
    </div>
    <section class="card table-wrap">
      <table>
        <thead>
          <tr>
            <th>Nome</th>
            <th>Identificador</th>
            <th>Tipo</th>
            <th>Localizacao</th>
            <th>Status</th>
            <th>Acoes</th>
          </tr>
        </thead>
        <tbody>
          ${rows || '<tr><td colspan="6">Nenhum dispositivo cadastrado.</td></tr>'}
        </tbody>
      </table>
      <p class="error" id="device-error" hidden></p>
    </section>
  `;
}
