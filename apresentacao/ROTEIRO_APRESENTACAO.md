# Roteiro da apresentação final — 07/11/2026

Pitch de **cerca de 10 minutos** com os slides de `EdgeHealth_Apresentacao_Final.pptx` + **demonstração ao vivo de 5 minutos** no site hospedado. As falas completas de cada slide estão nas **notas do apresentador** (no PowerPoint: Exibir → Anotações, ou o Modo de Exibição do Apresentador).

## Divisão por integrante

| Slide | Conteúdo | Quem fala | Tempo |
| --- | --- | --- | --- |
| 1 | Capa: EdgeHealth, turma e equipe | Marcelo Domingos | 0:25 |
| 2 | O problema e o público-alvo | Marcelo Domingos | 0:45 |
| 3 | Solução e como funciona (coletor → servidor → diagnóstico → prejuízo → IA) | Marcelo Domingos | 0:50 |
| 4 | Caso de uso 1: cadastrar dispositivo (entrada de dados) | Marcelo Rodrigues Alves do Nascimento | 0:35 |
| 5 | Caso de uso 2: coletor envia medições e o sistema detecta a falha (entrada de dados) | Marcelo Rodrigues Alves do Nascimento | 0:45 |
| 6 | Caso de uso 3: ocorrência, com diagnóstico, impacto e prejuízo (entrada de dados) | Erick Daniel Coelho E Silva | 0:50 |
| 7 | Caso de uso 4: histórico de falhas (recuperação de dados) | Erick Daniel Coelho E Silva | 0:30 |
| 8 | Caso de uso 5: visão da rede/dashboard (recuperação de dados) | Felipe Barbosa Poeiras | 0:40 |
| 9 | Arquitetura cliente-servidor | Felipe Barbosa Poeiras | 0:40 |
| 10 | Tecnologias | Felipe Barbosa Poeiras | 0:30 |
| 11 | API em camadas: árvore de diretórios | Matheus Brito Vaz Bernardes | 0:45 |
| 12 | Diagrama de classes | Matheus Brito Vaz Bernardes | 0:30 |
| 13 | Banco de dados e SQL nos Repositories | Matheus Brito Vaz Bernardes | 0:35 |
| 14 | README: 27 funcionalidades implementadas, 6 principais | João Lucas Santos Batista | 0:35 |
| 15 | Bônus (IA, hospedagem, termos) e qualidade (testes, segurança) | João Lucas Santos Batista | 0:50 |
| 16 | Demonstração ao vivo + links + encerramento | João Lucas Santos Batista | 0:20 |
| | **Total dos slides** | | **10:05** |

Tempo por pessoa: Marcelo Domingos 2:00 · Marcelo Rodrigues 1:20 · Erick 1:20 · Felipe 1:50 · Matheus 1:50 · João Lucas 1:45.

Cada um termina passando a vez pelo nome ("agora o Erick mostra...") — as frases de transição já estão nas notas.

## Demonstração ao vivo (5 minutos)

Uma pessoa opera o notebook (sugestão: **Marcelo Domingos**, que cuida do laboratório); a narração pode ser de quem falou o assunto nos slides. É o mesmo roteiro do vídeo ([docs/ROTEIRO_VIDEO.md](../docs/ROTEIRO_VIDEO.md)), sem a abertura e sem a arquitetura, que os slides já cobriram. O número entre colchetes é o da tabela "Funcionalidades Implementadas" do README.

| Tempo | Na tela | Quem narra | O que dizer |
| --- | --- | --- | --- |
| 0:00–0:20 | Terminal: `python tests\lab\edgelab.py falha offline desktop`. Volta ao site. | Marcelo Domingos | "Acabamos de desligar o Desktop do financeiro no nosso laboratório. Vamos ver o sistema detectar sozinho." |
| 0:20–1:00 | **Visão da rede** [26]: cards, gráficos, ranking de custo, coletor "Ativo". | Felipe | "Essa é a visão da rede ao vivo, com o ranking dos aparelhos que mais custaram." |
| 1:00–1:20 | **Histórico de falhas** [21]: estado "Abertas" → **Filtrar**. Abre a Impressora. | Erick | "A impressora caiu antes da apresentação; o coletor detectou e o servidor abriu a ocorrência [20]." |
| 1:20–2:00 | Ocorrência: **Severidade**, **Diagnóstico** (LOCALIZADA) e **Recomendações** [22]. | Erick | "Só ela parou e os outros respondem: problema localizado, e as recomendações do que verificar." |
| 2:00–2:40 | **Prejuízo estimado** [24] → **Impacto operacional**: 12 usuários → **Salvar impacto** [23]. | Felipe | "Com doze pessoas afetadas, o prejuízo é recalculado e a severidade sobe para alta." |
| 2:40–3:30 | **Explicar com IA** [25]. | João Lucas | "O Gemini recebe só dados técnicos e explica em linguagem simples. A IA explica; quem diagnostica é o sistema." |
| 3:30–4:00 | Histórico → **Filtrar**: aparece o Desktop [20]. | Marcelo Rodrigues | "E o Desktop que desligamos no começo já virou uma ocorrência, sem ninguém cadastrar nada." |
| 4:00–4:30 | **Relatórios** [27] → **Exportar dados da empresa** → abre o ZIP. | Matheus | "O relatório sai num ZIP com as planilhas de dispositivos, métricas, falhas e diagnósticos." |
| 4:30–5:00 | Terminal: `python tests\lab\edgelab.py falha restaurar todos`. Volta ao slide 16. | Marcelo Domingos | "Religamos tudo; em dois minutos o sistema confirma a recuperação. Obrigado! Perguntas?" |

**Importante:** derrube a Impressora **pelo menos 10 minutos antes** da demonstração (ver checklist). Falhas que começam a menos de 5 minutos uma da outra são correlacionadas pelo `AtualizarDiagnosticosService`, e a Impressora ganharia a hipótese COMPARTILHADA junto com o Desktop. (Se acontecer, não é erro: expliquem que duas quedas quase juntas levam o sistema a suspeitar de infraestrutura compartilhada.)

### Se a falha demorar

- O Desktop não apareceu em 3:30: clique em **Filtrar** de novo; se ainda não, diga "a coleta é a cada minuto" e abra uma ocorrência já registrada (filtro "Encerradas") ou o "Host inexistente (TEST-NET)", que está OFFLINE de propósito.
- A Impressora não está OFFLINE: use o TEST-NET (diagnóstico, severidade CRITICA e prejuízo).
- **Explicar com IA** deu erro: mostre a mensagem clara do sistema ("serviço sobrecarregado/cota") e siga; o vídeo gravado tem esse trecho funcionando.

## Plano B se a internet falhar

1. **Vídeo gravado** (o mesmo de [docs/ROTEIRO_VIDEO.md](../docs/ROTEIRO_VIDEO.md)): guardado **no notebook** (não só na nuvem) e num **pendrive**. Abra no player do Windows e narre por cima, na mesma ordem da demonstração.
2. Se nem o vídeo abrir: as capturas reais em `docs/img/telas/` (visão da rede, histórico, ocorrência, relatórios) e os slides de casos de uso 1–5.
3. Roteador do celular como internet de reserva (o laboratório e o coletor precisam de internet para enviar ao site).

## Checklist do dia

**Antes de 07/11**
- [ ] **Renovar o PythonAnywhere**: aba **Web** → botão **"Run until 1 month from today"** (o plano gratuito expira 1 mês após a última renovação; renovem na semana da apresentação).
- [ ] Ensaiar duas vezes com cronômetro (slides em até 10 min; demonstração em até 5 min).
- [ ] Gravar o vídeo e copiar para o notebook e para um pendrive.
- [ ] Entregar as credenciais de demonstração ao professor pelo **Google Classroom** (nunca no repositório nem nos slides).
- [ ] Testar o .pptx no computador da sala (ou levar também a versão em PDF).

**No dia, 15 minutos antes**
- [ ] Notebook **na tomada** (levar o **carregador**) e adaptador HDMI/USB-C.
- [ ] Internet conectada e testada (abrir o site).
- [ ] Subir o laboratório: `python tests\lab\edgelab.py subir` e conferir com `python tests\lab\edgelab.py status` (tudo ONLINE, menos o TEST-NET).
- [ ] Derrubar a Impressora: `python tests\lab\edgelab.py falha offline impressora` (pelo menos 10 min antes da demonstração).
- [ ] Navegador com a conta da Empresa TESTE LAB **logada**, numa janela só, zoom 100%, abas: Visão da rede e Histórico de falhas.
- [ ] Terminal aberto na raiz do projeto, fonte grande, com `python tests\lab\edgelab.py falha offline desktop` digitado sem Enter.
- [ ] Notificações desligadas (Não perturbe) e nenhum arquivo pessoal na área de trabalho.
- [ ] Testar **Explicar com IA** uma vez (limite de 10 por hora por empresa).
- [ ] Slides abertos no Modo de Exibição do Apresentador, no slide 1.

**Depois**
- [ ] `python tests\lab\edgelab.py descer`.
