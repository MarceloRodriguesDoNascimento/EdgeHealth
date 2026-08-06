export function Dispositivos() {
  return `
    <section>
      <h1>Dispositivos</h1>
      <form id="dispositivo-form">
        <input name="nome" placeholder="Nome" required />
        <input name="ip" placeholder="IP" required />
        <input name="tipo" placeholder="Tipo" />
        <input name="setor" placeholder="Setor" />
        <button type="submit">Cadastrar</button>
      </form>
      <hr />
      <h2>Lista de dispositivos</h2>
      <ul id="dispositivos-lista"></ul>
    </section>
  `;
}
