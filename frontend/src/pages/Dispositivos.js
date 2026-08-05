export function Dispositivos() {
  return `
    <section>
      <h1>Dispositivos</h1>
      <form id="dispositivo-form">
        <input name="nome" placeholder="Nome" required />
        <input name="identificador" placeholder="Identificador" required />
        <button type="submit">Cadastrar</button>
      </form>
      <ul id="dispositivos-lista"></ul>
    </section>
  `;
}
