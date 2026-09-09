# Estado da implementação

Branch: `feat/edgehealth-mvp`. Base: `fc60d981e783270e3d6caeed72f88bd1d9e91029`. Revisão: 09/09/2026.

Implementação retomada e preservada. Escopo de código TASK-001–TASK-032 coberto; detalhes e limites de aceite em [POST_IMPLEMENTATION_REVIEW.md](POST_IMPLEMENTATION_REVIEW.md).

- Backend: 30 testes aprovados, 1 teste ICMP opcional pulado na suíte padrão; cobertura de linhas de 93%.
- Frontend: build e 15 testes aprovados, com formulários, HTTP real, banco migrado, datasets, download e proxy Vite.
- Migrations 55463d3f0b18 e 7c7ba005affc verificadas do zero; comparação com modelos sem divergências; importação legada testada.
- Instalações isoladas verificadas. Backend validado também com dependências reinstaladas offline a partir do cache.
- ICMP habilitado explicitamente: 1 teste falhou com PermissionError/SocketPermissionError, antes do envio de pacotes. RF08–RF10 aguardam homologação em ambiente que permita ICMP e alcance a LAN.
- Nenhuma medição simulada foi introduzida no produto. Adaptadores controlados e dados determinísticos existem somente nos testes.
- Próximo trabalho de campo: roteiro em [DEMO.md](DEMO.md), sem reiniciar implementação ou reverter arquivos.

Para verificar: siga os comandos do [README](../README.md). Use o lock para recriar a venv se necessário. Confirme `git status` antes de modificar arquivos em uma nova sessão.
