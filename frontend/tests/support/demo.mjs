// Demonstração local com dados fictícios
process.env.UI_SERVER_PORT ||= '5180';
const {startApi, launch, seed, api} = await import('./live.js');

const stack = await startApi();
const browser = await launch();
if (!browser) throw new Error('Nenhum Chrome/Edge encontrado (defina EDGEHEALTH_BROWSER).');
const {admin} = await seed(browser, stack);
const extras = ['Roteador da matriz', 'Firewall', 'Access point da recepção', 'Access point do financeiro', 'Desktop do financeiro',
  'Câmera do estacionamento', 'Servidor de backup', 'Notebook da diretoria', 'Impressora do RH', 'Telefone IP da portaria'];
for (const [i, nome] of extras.entries()) {
  const device = await api(admin, 'POST', '/api/dispositivos', {nome, ip: `10.20.40.${i + 10}`, tipo: 'Outro', localizacao: 'Matriz'});
  if (i < extras.length - 1) for (let n = 0; n < 6; n++) await stack.probe(device.id, 4, 4 + n * 2);
}
await browser.close();
console.log(`Demonstração em ${stack.base}`);
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, async () => { await stack.close(); process.exit(0); });
setInterval(() => {}, 60000);
