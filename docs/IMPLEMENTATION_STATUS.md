# Estado da implementação (checkpoint)

Atualizado em **06/10/2026** (America/Sao_Paulo).

## Referência

- Branch: `feat/edgehealth-mvp`, **publicada** em `origin` (`MarceloRodriguesDoNascimento/EdgeHealth`). A PR #1 para `main` está aberta.
- Commit de partida desta etapa: `4320fb6`. Com autorização do usuário, as alterações desta etapa foram registradas em três commits e enviadas a `origin/feat/edgehealth-mvp` em 06/10/2026, atualizando a PR #1. Os hashes estão em `git log`. Não houve merge na `main` nem force push.
- Correção: as notas anteriores diziam que a publicação estava bloqueada por autenticação (`403` da integração, `api.github.com` bloqueado). Em 06/10/2026, `gh auth status` confirmou sessão válida, a branch remota coincide com o commit local e a PR foi aberta. O bloqueio não existe mais.

## Concluído nesta etapa

- Coletor remoto: modelo, migration `bc4dfbaec175`, credenciais, ingestão idempotente, heartbeat, telas e cliente em `collector/`.
- Termos/LGPD: aceite versionado, minutas públicas, retenção, anonimização, backup.
- Hospedagem: ProxyFix, HSTS, Dockerfile, compose e `docs/DEPLOY.md`.
- Documentação: README, DEMO, LGPD, DEPLOY, `collector/README.md`, revisão com a matriz RF.

## Testes executados (resultados reais, 06/10/2026)

- Backend: 46 aprovados, 2 pulados; cobertura de 94%.
- Rede real (`EDGEHEALTH_TEST_REAL_NETWORK=1`): 2 aprovados.
- Frontend: build aprovado e 16 testes aprovados.
- Migrations: banco vazio, reaplicação, `db check`, downgrade/upgrade em banco vazio, atualização de `7c7ba005affc` com dados.
- Ponta a ponta com Waitress, o processo coletor e ICMP real (detalhes em `DEPLOY.md` §7).

## Em andamento

Nada em andamento no código.

## Bloqueios e pendências externas

1. Homologar queda e **recuperação** com equipamento autorizado na rede da demonstração (`DEMO.md`).
2. Escolher e autorizar o provedor de hospedagem (custo, domínio, TLS, volume). Construir e testar a imagem Docker em máquina com Docker.
3. Definir controlador, encarregado e contatos; revisar as minutas jurídicas com os professores.
4. Homologação visual nos navegadores da apresentação.

## Próximo passo exato

1. Escolher, junto com o usuário, um equipamento que possa ser desconectado com segurança (nunca o roteador nem a conexão compartilhada).
2. Executar o `DEMO.md` (queda e recuperação reais) e registrar o resultado.
3. Escolher o provedor de hospedagem a partir das opções apresentadas; nada contratado ou publicado antes disso.

## Para retomar em nova sessão

Execute `git status` e confira se o working tree contém as alterações acima. Na pasta `backend`, com o ambiente virtual ativo, rode `python -m pytest -q`. Na pasta `frontend`, rode `npm test`. Não reinicie a implementação nem reverta arquivos.
