# EdgeHealth — privacidade e proteção de dados (LGPD)

> **Minuta técnica para revisão** pelos responsáveis do projeto e pelos professores. Não é parecer jurídico e não declara conformidade integral com a Lei nº 13.709/2018 (LGPD). Campos entre colchetes devem ser preenchidos pelos responsáveis; nada aqui foi inventado sobre pessoas, endereços, contratos ou provedores.

Fontes oficiais consultadas: [Lei nº 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) e [Resolução CD/ANPD nº 15/2024 — Regulamento de Comunicação de Incidente de Segurança](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-aprova-o-regulamento-de-comunicacao-de-incidente-de-seguranca).

## 1. Papéis

| Papel | Quem | Observação |
|---|---|---|
| Controlador dos dados das contas e da operação da plataforma | [responsável pela operação do EdgeHealth — a definir] | Define finalidades e meios do serviço hospedado. |
| Empresa cliente | Cada empresa cadastrada | Decide quais equipamentos e pessoas cadastra. Pode atuar como controladora dos dados que insere (ex.: nomes de colaboradores, localização de equipamentos). A relação exata deve ser definida nos termos firmados. |
| Encarregado (DPO) | [a definir] | Canal de contato: [a definir]. |
| Provedores (operadores) | [hospedagem ainda não escolhida] | Registrar aqui somente provedores efetivamente contratados (seção 6). |

## 2. Inventário de dados tratados (o que o código realmente armazena)

| Dado | Tabela / origem | Pessoal? | Finalidade | Base legal sugerida (art. 7º) | Retenção |
|---|---|---|---|---|---|
| Nome e e-mail do usuário | `usuarios` | Sim | Identificação, login, administração da equipe | Execução de contrato (V) | Enquanto a conta existir; anonimização sob pedido (seção 4) |
| Hash de senha (scrypt) | `usuarios.senha_hash` | Dado de autenticação | Autenticação | Execução de contrato (V) | Idem; substituído na anonimização |
| Papel, situação, aceite dos termos (versão e data) | `usuarios` | Sim (vinculado à conta) | Autorização; prova do aceite | Execução de contrato (V) / exercício regular de direitos (VI) | Enquanto a conta existir |
| Sessões (hash do token, hash CSRF, expiração) | `auth_sessions` | Sim (vinculado à conta) | Segurança da sessão | Execução de contrato (V) | Até a expiração (padrão 8 h); removidas no logout e pelo `purge-history` |
| Tentativas de login (hash de IP + e-mail) | `login_attempts` | Pseudonimizado | Prevenção de força bruta | Legítimo interesse (IX) / segurança | 15 min na lógica de bloqueio; removidas após 1 dia pelo `purge-history` |
| Dados da empresa (nome, CNPJ, e-mail, telefone) | `empresas` | Em regra dado de pessoa jurídica; e-mail/telefone podem identificar pessoa natural | Cadastro do cliente | Execução de contrato (V) | Enquanto a conta da empresa existir |
| Inventário (nome, IP, tipo, localização do equipamento) | `dispositivos` | Normalmente não; **pode ser** se o nome/localização identificar uma pessoa (ex.: "Notebook da Maria") ou o IP estiver associado a uma pessoa | Monitoramento | Execução de contrato (V) | Enquanto ativo; arquivado preserva histórico |
| Métricas (latência, perda, horário) | `metricas` | Normalmente não; idem acima quando o equipamento é pessoal | Histórico, diagnóstico | Execução de contrato (V) | **180 dias** (`METRIC_RETENTION_DAYS`) |
| Falhas, impacto, diagnóstico | `falhas`, `impactos`, `diagnosticos` | Normalmente não; a observação do impacto é texto livre | Histórico operacional e relatórios | Execução de contrato (V) | Mantidos enquanto a conta existir (volume pequeno); revisar com os responsáveis |
| Coletores (nome, hash da credencial, versão, último contato) | `coletores` | Não | Autenticação de agentes | Execução de contrato (V) | Enquanto a conta existir |
| Logs do servidor e do coletor | saída padrão | Podem conter IPs de equipamentos e IDs | Operação e incidentes | Legítimo interesse (IX) | Definir no provedor: sugestão 30 dias |
| Backups | arquivos gerados por `flask backup` | Sim (cópia integral) | Recuperação | Legítimo interesse (IX) | Sugestão: 7 diários + 4 semanais; armazenamento com acesso restrito |
| Registros legados importados | `registros_legados` | Podem conter dados pessoais (credenciais são removidas na importação) | Revisão da migração | Legítimo interesse (IX) | Excluir após a revisão do operador |

**Não coletados:** dados sensíveis (art. 5º, II), dados de crianças, geolocalização de pessoas, conteúdo de tráfego, cookies de terceiros, analytics ou rastreamento. Os cookies são somente de sessão e CSRF, estritamente necessários.

Bases legais são **sugestões** a validar. O sistema **não usa consentimento** como base universal: o aceite dos Termos de Uso e a ciência do Aviso de Privacidade são registrados separadamente (versão e data em `usuarios`) e não se confundem com consentimento (art. 7º, I).

## 3. Medidas técnicas implementadas (art. 46)

- **Minimização:** o cadastro exige só o necessário; o número de usuários afetados é estimativa numérica, sem identificação de pessoas; nenhum dado de navegação é coletado.
- **Controle de acesso:** sessão opaca com hash no banco, cookies HttpOnly/SameSite=Lax e `Secure` com HTTPS, CSRF, expiração, revogação no logout, na troca de senha ou de permissão, e limite de tentativas.
- **Segregação entre empresas:** todas as consultas usam a empresa da sessão; IDs de outra empresa retornam 404 (testes `test_tenants_reports.py`, `test_isolation_reports.py`, `test_collectors.py`).
- **Credenciais de coletor:** exibidas uma única vez; o servidor guarda somente o hash SHA-256; rotação e revogação imediatas; o coletor não escolhe a empresa.
- **Transporte:** o coletor exige HTTPS (HTTP só em localhost ou com `--allow-http` em laboratório); HSTS quando `COOKIE_SECURE=true`.
- **Logs:** tokens, senhas e cookies não são registrados; mensagens de erro ao cliente não expõem detalhes internos.
- **Retenção:** `flask purge-history` (padrão 180 dias; mínimo 30) remove amostras brutas antigas, sessões expiradas e tentativas de login antigas. Execute diariamente (agendador do sistema).
- **Anonimização sob pedido:** `flask anonymize-user --email ... --yes` substitui nome e e-mail, invalida a senha, desativa a conta e revoga sessões, mantendo o histórico operacional da empresa sem identificar a pessoa.
- **Backups:** `flask backup --output ...` gera cópia consistente e verificada, sem sobrescrever arquivos. Backups contêm dados pessoais: guarde-os criptografados e com acesso restrito.
- **Exportação CSV** protegida contra injeção de fórmulas.

## 4. Atendimento a titulares (art. 18)

1. Receber o pedido pelo canal do encarregado: [a definir].
2. Confirmar a identidade do solicitante, por exemplo resposta a partir do e-mail cadastrado. Nunca enviar dados a terceiros.
3. Identificar a empresa vinculada. Quando a empresa cliente for a controladora, encaminhar o pedido a ela e apoiá-la.
4. Conforme o pedido:
   - **acesso/confirmação:** consultar `usuarios` (nome, e-mail, papel, situação, datas de aceite);
   - **correção:** o administrador da empresa edita em **Equipe**;
   - **eliminação/anonimização:** `python -m flask --app run.py anonymize-user --email <e-mail> --yes`. A pessoa não pode ser a única administradora ativa: antes, promova outra;
   - **portabilidade:** exportar os campos acima em formato estruturado.
5. Registrar data, pedido, decisão e resposta. Prazo de referência: art. 19 da LGPD.

## 5. Resposta a incidentes de segurança

1. **Conter:** revogar credenciais de coletor comprometidas (tela **Coletores**); desativar contas afetadas; trocar segredos do servidor; isolar o host.
2. **Preservar evidências:** logs e cópia do banco (`flask backup`), sem alterar o original.
3. **Avaliar:** quais dados, quantas pessoas, quais empresas. Hashes de senha e de sessão são dados de autenticação, o que é um dos critérios de risco relevante do regulamento da ANPD.
4. **Comunicar:** se houver risco ou dano relevante, o controlador comunica à ANPD e aos titulares em **3 dias úteis** a partir do conhecimento de que o incidente afetou dados pessoais (Resolução CD/ANPD nº 15/2024). Avisar as empresas clientes afetadas.
5. **Registrar** o incidente, mesmo sem comunicação, e as medidas adotadas.
6. **Corrigir** a causa e revisar este documento.

Credenciais expostas no histórico Git devem ser revogadas e rotacionadas. O histórico não deve ser reescrito automaticamente.

## 6. Provedores efetivamente utilizados

| Provedor | Serviço | Localização dos dados | Contrato/termos |
|---|---|---|---|
| — | Nenhum provedor de hospedagem contratado até esta revisão | — | — |

Preencha ao contratar hospedagem, backup externo ou e-mail. Avalie a transferência internacional (arts. 33 a 36) se os servidores estiverem fora do Brasil.

## 7. Pendências para os responsáveis

- [ ] Definir controlador, encarregado e canal de contato.
- [ ] Revisar as bases legais sugeridas e as minutas em `frontend/public/termos.html` e `frontend/public/privacidade.html`.
- [ ] Definir a retenção de logs e backups no provedor escolhido.
- [ ] Registrar os provedores contratados.
- [ ] Agendar `purge-history` e backups no ambiente hospedado.

Ao alterar os Termos, aumente `TERMS_VERSION`: cada usuário aceitará a nova versão no próximo acesso.
