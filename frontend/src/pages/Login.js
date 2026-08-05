export function Login() {
  return `
    <section>
      <h1>Login</h1>
      <form id="login-form">
        <input name="email" type="email" placeholder="Email" required />
        <input name="senha" type="password" placeholder="Senha" required />
        <button type="submit">Entrar</button>
      </form>
    </section>
  `;
}
