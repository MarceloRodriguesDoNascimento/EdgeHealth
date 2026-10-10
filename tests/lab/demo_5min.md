# Demonstração ao vivo (5 minutos)

**Antes de começar (10 min antes):**

1. `python tests\lab\edgelab.py subir` e espere ~2 min.
2. `python tests\lab\edgelab.py status`: todos ONLINE, exceto o TEST-NET (OFFLINE de propósito).
3. No navegador, entre como a Empresa TESTE LAB e deixe abertas a **Visão da rede** e o **Histórico de falhas**.
4. Deixe um terminal pronto na pasta do projeto.

| Tempo | Ação no terminal | O que mostrar na tela |
|---|---|---|
| 0:00 | — | Visão da rede: 12 dispositivos de tipos diferentes, coletor ATIVO e o TEST-NET OFFLINE (falha CRITICA por estar fora há mais de 1 h). |
| 0:30 | `python tests\lab\edgelab.py falha offline impressora` | Explique: o coletor mede por ICMP a cada 60 s; 1 amostra ruim abre a ocorrência, 3 confirmam a indisponibilidade. |
| 1:30 | — | A Impressora fica INSTÁVEL e a ocorrência aparece no histórico. |
| 3:00 | `python tests\lab\edgelab.py falha switch down` | Impressora OFFLINE: abra a falha e mostre o diagnóstico **LOCALIZADA** (os outros respondem) e as recomendações. Em seguida, derrube o switch do andar 2. |
| 4:00 | — | AP, Câmera, VoIP e o Switch ficam INSTÁVEIS ao mesmo tempo: explique a correlação na janela de 5 min. Se der tempo, a falha do Switch já mostra **COMPARTILHADA** e severidade ALTA (~3 min após a queda). |
| 4:30 | `python tests\lab\edgelab.py falha restaurar todos` | Mostre que a recuperação exige 2 amostras boas (~2 min) e que o diagnóstico fica preservado na falha encerrada. |

**Plano B:** se a rede da apresentação falhar, mostre os prints em `tests/lab/screenshots/` e o `tests/lab/relatorio.md` da execução noturna.

**Depois:** `python tests\lab\edgelab.py descer`.
