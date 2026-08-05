export function renderLogin() {
  return `
    <section class="auth-layout">
      <div class="auth-panel">
        <div class="auth-banner">
          <div>
            <div class="brand-mark">EH</div>
            <h1>EdgeHealth</h1>
            <p>Monitoramento de dispositivos, metricas e falhas operacionais.</p>
          </div>
          <p>Backend Flask + frontend estatico prontos para evoluir.</p>
        </div>

        <div class="auth-forms">
          <div class="tabs" role="tablist">
            <button class="active" id="login-tab" type="button">Entrar</button>
            <button id="register-tab" type="button">Cadastrar</button>
          </div>

          <form class="form" id="login-form">
            <label>
              Email
              <input name="email" type="email" autocomplete="email" required />
            </label>
            <label>
              Senha
              <input name="senha" type="password" autocomplete="current-password" required />
            </label>
            <button class="primary-button" type="submit">Entrar</button>
            <p class="error" id="login-error" hidden></p>
          </form>

          <form class="form hidden" id="register-form">
            <label>
              Nome
              <input name="nome" autocomplete="name" required />
            </label>
            <label>
              Email
              <input name="email" type="email" autocomplete="email" required />
            </label>
            <label>
              Senha
              <input name="senha" type="password" autocomplete="new-password" required />
            </label>
            <label>
              Empresa
              <input name="empresa_nome" required />
            </label>
            <button class="primary-button" type="submit">Cadastrar</button>
            <p class="error" id="register-error" hidden></p>
          </form>
        </div>
      </div>
    </section>
  `;
}
