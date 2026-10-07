import { el, label, input, form, button, brandLogo } from '../ui/dom.js';
import { apiFetch, json } from '../services/api.js';

export function Login(onSuccess, registration = false) {
  const intro = el('div', { className: 'auth-intro' },
    el('div', { className: 'brand light' }, brandLogo(), el('span', { 'aria-hidden': 'true' }, 'EdgeHealth')),
    el('div', {}, el('span', { className: 'eyebrow' }, 'MONITORAMENTO DE REDE'),
      el('h1', {}, 'Entenda o que acontece na sua rede.'),
      el('p', {}, 'Acompanhe dispositivos, investigue ocorrências e consulte o histórico em um só lugar.')),
    el('p', { className: 'auth-footer' }, 'Disponibilidade · Diagnóstico · Histórico'));
  const fields = [];
  if (registration) fields.push(
    label('Nome da empresa', input('nome_fantasia', 'Nome fantasia', { required: true, maxLength: 150 })),
    label('CNPJ', input('cnpj', '00.000.000/0000-00', { required: true, maxLength: 18 })),
    label('Seu nome', input('nome', 'Nome completo', { required: true, maxLength: 100 })));
  fields.push(label('E-mail', input('email', 'voce@empresa.com.br', { type: 'email', required: true, autoComplete: 'username' })),
    label('Senha', input('senha', registration ? 'Pelo menos 10 caracteres' : 'Sua senha', { type: 'password', required: true, minLength: registration ? 10 : 1, maxLength: 128, autoComplete: registration ? 'new-password' : 'current-password' })));
  if (registration) fields.push(termsCheckbox());
  const surface = el('div', { className: 'auth-form' }, el('span', { className: 'eyebrow' }, registration ? 'PRIMEIRO ACESSO' : 'BEM-VINDO'),
    el('h2', {}, registration ? 'Cadastre sua empresa' : 'Acesse sua rede'),
    el('p', { className: 'muted' }, registration ? 'Você será o administrador e poderá cadastrar a equipe.' : 'Entre com o e-mail cadastrado pela sua empresa.'),
    form(fields, registration ? 'Criar empresa e conta' : 'Entrar', async data => {
      if (registration) data.aceite_termos = data.aceite_termos === 'on';
      onSuccess(await apiFetch(registration ? '/auth/registro' : '/auth/login', { method: 'POST', body: json(data) }));
    }),
    button(registration ? 'Já tenho uma conta' : 'Cadastrar minha empresa', () => document.querySelector('#app').replaceChildren(Login(onSuccess, !registration)), 'link'),
    legalLinks());
  return el('main', { className: 'auth-layout' }, intro, surface);
}

const legalLinks = () => el('p', { className: 'muted small legal-links' },
  el('a', { href: '/termos.html', target: '_blank', rel: 'noopener' }, 'Termos de Uso'), ' · ',
  el('a', { href: '/privacidade.html', target: '_blank', rel: 'noopener' }, 'Aviso de Privacidade'));

function termsCheckbox() {
  return el('label', { className: 'checkbox full' }, el('input', { type: 'checkbox', name: 'aceite_termos', required: true }),
    el('span', {}, 'Li e aceito os ', el('a', { href: '/termos.html', target: '_blank', rel: 'noopener' }, 'Termos de Uso'),
      ' e declaro ciência do ', el('a', { href: '/privacidade.html', target: '_blank', rel: 'noopener' }, 'Aviso de Privacidade'), '.'));
}

// Shown when the account has not accepted the current version of the Terms (e.g. created by an administrator).
export function TermsPending(session, onAccepted, onLogout) {
  return el('main', { className: 'auth-layout' }, el('div', { className: 'auth-form' },
    el('span', { className: 'eyebrow' }, 'TERMOS DE USO'),
    el('h2', {}, 'Antes de continuar'),
    el('p', { className: 'muted' }, `${session.usuario.nome}, leia os documentos abaixo. O acesso aos dados da empresa é liberado após o aceite da versão atual.`),
    form([termsCheckbox()], 'Aceitar e continuar', async data => {
      onAccepted(await apiFetch('/auth/aceite-termos', { method: 'POST', body: json({ aceite_termos: data.aceite_termos === 'on' }) }));
    }),
    button('Sair', onLogout, 'link')));
}
