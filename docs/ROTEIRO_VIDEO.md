# Roteiro do vídeo de demonstração (máximo 5 minutos)

Vídeo obrigatório da disciplina: sem ele o projeto não é avaliado. Duração planejada: **4 min 45 s** (15 s de folga).

O que o vídeo precisa mostrar, e onde isso acontece no roteiro:

| Exigência | Trecho |
| --- | --- |
| Funcionalidades de ponta a ponta, com interação na interface e resultado no sistema | todos |
| Pelo menos 4 funcionalidades principais não-CRUD (★ no README) | ★20 detecção pelo coletor, ★22 diagnóstico, ★24 prejuízo, ★25 IA, ★26 dashboard com ranking, ★27 relatório |
| Correspondência com o README | cada trecho cita o número da funcionalidade da tabela "Funcionalidades Implementadas" |
| Arquitetura em camadas e diagrama de classes (10–15 s, sem ler código) | 04:00–04:15 |
| Site hospedado | <https://marcelodomingos.pythonanywhere.com>, conta da **Empresa TESTE LAB** |

## Preparação (30 minutos antes de gravar)

- [ ] **Dia e horário:** grave num dia útil entre 08:00 e 18:00. O prejuízo (★24) só conta horas dentro do expediente configurado para a Empresa TESTE LAB (seg–sex, 08:00–18:00); fora dele, a falha nova mostra R$ 0,00.
- [ ] **Subir o laboratório** (na raiz do projeto, PowerShell): `python tests\lab\edgelab.py subir` e esperar uns 2 minutos.
- [ ] `python tests\lab\edgelab.py status`: tudo ONLINE, menos o "Host inexistente (TEST-NET)", que fica OFFLINE de propósito.
- [ ] **Provocar a falha principal antes de gravar** (10 minutos antes): `python tests\lab\edgelab.py falha offline impressora`. Assim, durante o vídeo, a Impressora já estará OFFLINE com diagnóstico e prejuízo calculados. Não encurte esse intervalo: falhas que começam a menos de 5 minutos uma da outra são correlacionadas (`AtualizarDiagnosticosService`), e a Impressora ganharia a hipótese COMPARTILHADA junto com o Desktop do trecho 00:20.
- [ ] **Navegador:** só uma janela, sem outras abas, sem favoritos visíveis, zoom em 100%. Entre no site com a conta da Empresa TESTE LAB (credenciais com quem cuida do laboratório; elas não aparecem no vídeo nem no repositório).
- [ ] Deixe abertas, nesta ordem: **Visão da rede**, **Histórico de falhas** e a ocorrência da Impressora (plano B, ver abaixo).
- [ ] **Terminal** (PowerShell) aberto na raiz do projeto, fonte grande (Ctrl + roda do mouse), com o comando do trecho 00:20 já digitado, sem apertar Enter.
- [ ] **VS Code** aberto na pasta `backend/` com a árvore de arquivos expandida em `controllers`, `services`, `models` e `repositories`, e o arquivo `docs/img/diagrama-classes.png` numa aba.
- [ ] **Tela:** resolução 1920×1080, escala do Windows em 100% ou 125%, notificações desligadas (Foco/Não perturbe), barra de tarefas sem nada pessoal.
- [ ] **Microfone:** fone com microfone ou o do notebook num lugar silencioso; grave 10 s de teste e ouça.
- [ ] Teste o botão **Explicar com IA** uma vez antes (limite de 10 por hora por empresa).

### Ferramenta de gravação (gratuita, Windows)

- **Xbox Game Bar** (já vem no Windows): `Win + Alt + R` inicia e para. Grava só uma janela, então use o navegador em tela cheia e troque de janela com `Alt + Tab` (o terminal e o VS Code também precisam aparecer: nesse caso prefira o OBS).
- **OBS Studio** (recomendado): fonte "Captura de tela", 1920×1080, 30 fps, saída MP4. Grava a tela inteira, inclusive a troca entre navegador, terminal e VS Code.

## Roteiro cronometrado

Falas em primeira pessoa do plural, curtas. O número entre colchetes é o da tabela "Funcionalidades Implementadas" do README.

| Tempo | Na tela | Fala |
| --- | --- | --- |
| **00:00–00:20** | Tela de login do site hospedado, com a URL visível. | "Oi, nós somos a equipe do EdgeHealth. Pequenas empresas só descobrem que a rede caiu quando alguém reclama, e não sabem o motivo nem quanto a parada custou. A gente fez um sistema que monitora a rede, explica a falha e estima o prejuízo. Ele está no ar, hospedado no PythonAnywhere." |
| **00:20–00:40** | Terminal: aperta Enter em `python tests\lab\edgelab.py falha offline desktop`. Volta ao navegador. | "Pra mostrar funcionando de verdade, montamos um laboratório com doze equipamentos de rede. Agora a gente acabou de desligar o Desktop do financeiro. Daqui a pouco vamos ver o sistema detectar isso sozinho." |
| **00:40–01:20** | **Visão da rede** [26]: cards de status, gráfico de latência, "Custo estimado das falhas" com o ranking, painel do coletor "Ativo". | "Essa é a visão da rede [26]. Aqui a gente vê quantos equipamentos estão online, instáveis e offline, os gráficos de latência e perda, e esse ranking: os aparelhos que mais custaram dinheiro com falhas nos últimos 30 dias. Quem mede tudo isso é o coletor, um programa que roda dentro da rede da empresa e manda as medições pro servidor." |
| **01:20–01:45** | Menu **Histórico de falhas** [21]: escolhe o estado "Abertas" e clica em **Filtrar**. Aparece a Impressora (OFFLINE) e, se já deu tempo, o Desktop. | "No histórico ficam todas as ocorrências. O coletor manda as medições, e o servidor decide se é instabilidade ou queda [20]: uma medição ruim abre a ocorrência e três seguidas confirmam que o equipamento caiu. Vamos abrir a da impressora." |
| **01:45–02:25** | Ocorrência da Impressora: card **Severidade**, **Diagnóstico lógico** (LOCALIZADA) e **Recomendações** [22]. | "Aqui está o diagnóstico [22]. O sistema comparou com os outros equipamentos: como só a impressora parou e o resto continua respondendo, a causa provável é um problema localizado, tipo cabo, porta ou energia. E ele já sugere o que fazer, nessa lista de recomendações. A severidade também é calculada sozinha, pela duração e pelo impacto." |
| **02:25–02:55** | Card **Prejuízo estimado** [24]: valor e a conta por extenso. Rolar até **Impacto operacional**, digitar 12 em "Usuários afetados", **Salvar impacto** [23]; o valor e a severidade mudam. | "Agora o prejuízo estimado [24]: o sistema mostra o valor e a conta aberta, horas de expediente vezes pessoas afetadas vezes custo por hora. Se a gente informa que doze pessoas dependiam dessa impressora [23]... salvou: o prejuízo foi recalculado e a severidade subiu, porque dez ou mais pessoas afetadas já é severidade alta." |
| **02:55–03:30** | Card **Explicação com IA** [25]: clica em **Explicar com IA**, espera o texto (uns 5 s) e passa o mouse pelos três parágrafos e pelo aviso. | "E pra quem não é técnico, tem o Explicar com IA [25]. A gente manda pro Gemini só dados técnicos da ocorrência, nunca nome, e-mail ou IP, e ele escreve em português simples o que aconteceu, o impacto e os próximos passos. A IA só explica; o diagnóstico continua sendo do nosso sistema." |
| **03:30–03:45** | Volta ao **Histórico de falhas** e clica em **Filtrar** de novo: aparece a ocorrência nova do Desktop (INSTÁVEL ou OFFLINE). | "E olha o Desktop que a gente desligou no começo do vídeo: o sistema já detectou e abriu a ocorrência sozinho [20], sem ninguém cadastrar nada." |
| **03:45–04:00** | Menu **Relatórios** [27]: clica em **Exportar dados da empresa**, abre o ZIP baixado e mostra os 5 arquivos. | "Por fim, o relatório [27]: um ZIP com as planilhas de dispositivos, métricas, falhas e diagnósticos, pra empresa guardar ou mandar pro gestor." |
| **04:00–04:15** | VS Code: árvore `backend/` com `controllers`, `services`, `models`, `repositories` e `database/create_database.sql`; troca para a aba do diagrama de classes. | "Por dentro, a API em Flask é organizada em camadas: controllers recebem as requisições, services têm um caso de uso cada, models fazem o CRUD e repositories as consultas SQL. Esse é o nosso diagrama de classes." |
| **04:15–04:35** | Terminal: `python tests\lab\edgelab.py falha restaurar todos`. Volta ao site, **Visão da rede**. | "O frontend em Vite e a API são aplicações separadas que conversam por HTTP. Agora a gente religa os equipamentos, e em uns dois minutos o sistema confirma a recuperação e encerra as ocorrências, guardando o histórico." |
| **04:35–04:45** | Página inicial do site com a URL. | "Esse foi o EdgeHealth. O código, os diagramas e a lista das funcionalidades estão no README do repositório. Obrigado!" |

## Plano B

| Problema | O que fazer sem parar a gravação |
| --- | --- |
| O Desktop ainda não apareceu no trecho 03:30 | Clique em **Filtrar** mais uma vez. Se não aparecer, diga: "a coleta é a cada minuto; enquanto isso, olhem essa outra queda que o coletor detectou" e abra uma ocorrência já registrada do Histórico (filtro "Encerradas" ou o TEST-NET, que está OFFLINE desde o início). |
| A Impressora não ficou OFFLINE antes de gravar | Abra o "Host inexistente (TEST-NET)": está OFFLINE de propósito, com diagnóstico, severidade CRITICA e prejuízo. |
| **Explicar com IA** respondeu erro (cota ou serviço sobrecarregado) | Diga: "o serviço do Google está sobrecarregado agora, e o sistema avisa isso com uma mensagem clara". Corte e regrave só esse trecho depois, ou use uma tomada anterior. |
| O site ou a internet caiu | Pare, grave de novo mais tarde. Se for perto do prazo, rode local (README, "Como executar") e mostre as telas de `docs/img/telas/` para o que depender do laboratório. |
| Passou de 5 minutos | Corte o trecho 03:45–04:00 (relatório) e encurte a fala da IA; nunca corte o trecho da arquitetura nem os ★ 20, 22, 24 e 25. |

Depois de gravar: `python tests\lab\edgelab.py descer`.

## Divisão das falas entre os 6 integrantes (opcional)

Se o grupo quiser que todos apareçam, cada um grava a própria voz no seu trecho (quem não puder falar ao vivo grava o áudio no celular e a edição encaixa). A tela continua sendo gravada por uma pessoa só.

| Trecho | Integrante | Assunto |
| --- | --- | --- |
| 00:00–00:40 | Marcelo Domingos | Problema, público e o laboratório |
| 00:40–01:45 | Marcelo Rodrigues Alves do Nascimento | Visão da rede, coletor e detecção (★26, ★20) |
| 01:45–02:25 | Erick Daniel Coelho E Silva | Diagnóstico e recomendações (★22) |
| 02:25–02:55 | Felipe Barbosa Poeiras | Prejuízo estimado e impacto (★24, 23) |
| 02:55–03:45 | Matheus Brito Vaz Bernardes | Explicação com IA e a detecção ao vivo (★25, ★20) |
| 03:45–04:45 | João Lucas Santos Batista | Relatório, arquitetura, diagrama e encerramento (★27) |

Dica: ensaiem com cronômetro pelo menos duas vezes. Se cada trecho for gravado separado, mantenham a mesma janela e o mesmo zoom para a edição ficar contínua.
