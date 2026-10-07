# Demonstração do EdgeHealth

Roteiro reproduzível. Use somente equipamentos e redes que a equipe administra e está autorizada a interromper. Não provoque quedas em equipamentos de produção, da escola ou de terceiros. Não há controles de simulação no produto: tudo o que aparece na tela vem de medições reais.

**Preparação** (comandos no [README](../README.md)):

- **Backend:** terminal 1, pasta `backend`, ambiente virtual ativo, `python run.py`.
- **Frontend:** terminal 2, pasta `frontend`, `npm run dev`, abrir `http://localhost:5173`. Alternativa: `npm run build` e acessar `http://localhost:5000`.
- **Coletor:** terminal 3, pasta `collector` ([collector/README.md](../collector/README.md)). Em ambiente hospedado, o coletor roda no notebook ligado à rede de teste e aponta para a URL HTTPS da hospedagem.
- **Alvo controlado:** um equipamento dedicado da rede de teste, por exemplo um roteador de laboratório, um Raspberry Pi ou uma VM com rede em modo bridge, que possa ser desligado ou desconectado sem afetar ninguém. Anote o IP real dele: não use endereços de exemplo.

## Roteiro

1. **Empresa:** em **Cadastrar minha empresa**, preencha os dados reais da equipe, marque o aceite dos Termos e crie a conta. Mostre os links de Termos e Privacidade (minutas).
2. **Login:** saia e entre de novo.
3. **Usuário:** em **Equipe**, cadastre um técnico. Entre com ele em outro navegador: primeiro aparece a tela de aceite dos Termos; depois o acesso é liberado, sem os menus de administração.
4. **Dispositivos:** cadastre o alvo controlado e um segundo alvo estável da mesma rede, por exemplo o gateway da rede de teste.
5. **Coletor:** em **Coletores**, cadastre "Coletor do laboratório" e copie a credencial (exibida uma vez). Em **Dispositivos → Editar → Origem da medição**, escolha esse coletor nos dois dispositivos. No terminal 3, inicie o coletor (sem `--once`). Em **Coletores**, a situação passa a **Ativo**.
6. **Coleta real:** em até 30 s, ambos ficam ONLINE, com horário, latência e perda. **Coletar** antecipa a próxima medição.
7. **Métricas e status:** em **Métricas**, confira pacotes enviados/recebidos, latência e ordem cronológica. Feche o navegador por um minuto e reabra: há novas amostras (a coleta não depende do site aberto).
8. **Indisponibilidade controlada:** desligue ou desconecte **somente** o alvo controlado. As primeiras ausências geram INSTÁVEL; três ciclos sem resposta confirmam OFFLINE. A latência fica "—" (desconhecida) e a perda vai a 100%.
9. **Abertura da falha:** em **Histórico de falhas**, aparece uma ocorrência com data, horário, dispositivo e severidade.
10. **Sem duplicação:** aguarde mais 2–3 ciclos. Continua **uma** ocorrência, com o mesmo ID; a duração e a "última observação" avançam.
11. **Detalhe:** abra a ocorrência. Mostre a severidade e sua justificativa, o diagnóstico `LOCALIZADA` (o outro dispositivo respondeu), as causas apresentadas como hipóteses, as recomendações e as evidências. Explique que ICMP bloqueado também produziria esse quadro.
12. **Impacto:** informe uma estimativa de usuários afetados (ex.: 12) com observação. A origem fica "informada pela equipe" e a severidade é recalculada. Ressalte que a duração é calculada e o número de usuários é estimativa manual.
13. **Restauração:** religue o alvo.
14. **Encerramento:** após duas coletas saudáveis, o dispositivo volta a ONLINE e a ocorrência fica ENCERRADA com motivo RECUPERAÇÃO, preservando o diagnóstico. Uma nova queda criaria outro ID.
15. **Histórico:** filtre por estado ENCERRADA e por dispositivo.
16. **Dashboard:** indicadores, gráficos de latência e perda do dispositivo (com lacuna no período sem resposta), severidades e situação do coletor.
17. **Exportação:** em **Relatórios**, gere o ZIP. Abra `dispositivos.csv`, `metricas.csv` (com `coletor_id`), `falhas.csv`, `diagnosticos.csv` e `leia-me.json`, e compare com a tela.
18. **Isolamento:** em outro navegador ou janela anônima, cadastre uma segunda empresa de teste. O inventário começa vazio. Um ID da primeira empresa digitado na URL da API (`/api/falhas/ID`) retorna 404, e a credencial do coletor da empresa 1 não envia dados para dispositivos da empresa 2.
19. **Coletor parado (opcional):** pare o coletor (Ctrl+C). Após 3 minutos, ele aparece como **Sem contato recente** e os dados como desatualizados. **Nenhuma** falha de dispositivo é criada. Reinicie: as amostras da fila local são enviadas.
20. **Interface hospedada:** quando houver hospedagem autorizada ([DEPLOY.md](DEPLOY.md)), repita os passos 5 a 17 com o coletor apontando para a URL HTTPS.

## Calendário

Referência: 06/10/2026, America/Sao_Paulo.

| Marco | Data | Dias corridos restantes |
|---|---|---|
| Entrega do MVP (20 funcionalidades) | 23/10/2026, sexta-feira | 17 |
| Revisão do MVP | 30/10/2026, sexta-feira | 24 |
| Apresentação final | 07/11/2026, sábado | 32 |

Antes do MVP:

- executar este roteiro completo na rede de teste da equipe, registrando data, IPs reais e prints;
- decidir e autorizar a hospedagem;
- revisar as minutas jurídicas com os professores;
- homologar os navegadores da apresentação.
