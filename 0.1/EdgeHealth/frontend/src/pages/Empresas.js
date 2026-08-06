export function Empresas() {
  return `
    <section>
      <h1>Empresas</h1>
      <form id="empresa-form">
        <input name="nome_fantasia" placeholder="Nome fantasia" required />
        <input name="cnpj" placeholder="CNPJ" required />
        <button type="submit">Cadastrar</button>
      </form>
      <hr />
      <h2>Lista de empresas</h2>
      <ul id="empresas-lista"></ul>
    </section>
  `;
}
