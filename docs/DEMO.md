# Demonstração do EdgeHealth

Use o README para instalar banco, catálogo, API, frontend e worker. Execute o coletor na LAN de teste. Não provoque interrupções em equipamentos de produção.

1. Execute `python -m flask --app run.py probe 127.0.0.1`. Deve apresentar contagens e latência reais. Se houver erro de permissão, adeque o ambiente antes de afirmar que a coleta funciona nesse computador.
2. Cadastre empresa e administrador pela interface, com senha própria. Cadastre um técnico em **Equipe** e mostre o vínculo automático com a empresa.
3. Cadastre dois alvos autorizados e responsivos: o próprio coletor (`127.0.0.1`) e uma VM/equipamento dedicado da LAN. Informe nome, IP, tipo e localização.
4. Mantenha `python -m flask --app run.py monitor` em outro terminal. Após a coleta, mostre ONLINE, horário, latência e perda. Feche o navegador por um minuto e reabra: novas amostras devem existir sem acesso à interface.
5. Abra **Métricas** e confira pacotes, filtros e ordenação. **Coletar** somente antecipa o agendamento; o worker continua responsável pela medição.
6. Interrompa somente a conectividade da VM dedicada, mantendo o outro alvo online. As primeiras ausências geram INSTAVEL; três coletas sem resposta confirmam OFFLINE. Latência deve ficar desconhecida e perda deve refletir as contagens.
7. No histórico, a ocorrência deve ter um único ID durante os ciclos de falha. Confira início, duração, severidade e justificativa.
8. Com o par online e observações recentes, mostre a hipótese LOCALIZADA e recomendações. Não afirme certeza de defeito físico: indisponibilidade ICMP também pode ser configuração.
9. Informe a quantidade de participantes realmente afetados na demonstração, ou deixe desconhecida. Mostre a origem manual e o recálculo da severidade. Duração é automática.
10. Restaure a VM. Após duas coletas saudáveis, deve ficar ONLINE e a mesma ocorrência deve encerrar por RECUPERACAO, conservando o diagnóstico. Uma queda posterior deve criar outro ID.
11. Confira dashboard: inventário, estados, ocorrências, severidades, latência e perda correspondem ao banco. Selecione dispositivo e período dos gráficos e atualize após novas coletas.
12. Gere o relatório e abra os quatro CSVs do ZIP. Compare IDs, medições, causas, evidências, recomendações e impacto com a interface.
13. Em outra sessão/navegador, cadastre outra empresa. Seu inventário inicia vazio; IDs de recursos da primeira empresa retornam 404. Não compartilhe a sessão nesse teste.
14. Arquive um dispositivo de teste. Ele sai do inventário ativo e deixa de ser coletado; permanece em **Incluir arquivados**, métricas, histórico e relatórios.

Não há controles de simulação no produto. Congestionamento e latência elevada somente devem ser demonstrados quando existirem essas condições reais em laboratório autorizado. Os testes exercitam esses cenários de forma determinística em banco descartável, separado do produto.

## Calendário informado

MVP: **23/10/2026, sexta-feira**. Revisão: **30/10/2026, sexta-feira**. Apresentação: **07/11/2026, sábado**. Em 09/09/2026 faltam 44 dias corridos para o MVP. A entrega das dez funcionalidades de 21/08 já está no passado.

Antes do MVP, execute este roteiro na LAN da equipe, registre o teste ICMP real e homologue os navegadores da apresentação. Isso encerra a pendência de campo que este ambiente não permite resolver.
