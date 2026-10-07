# Laboratório de rede do EdgeHealth

Rede simulada dentro do WSL2 (Ubuntu-24.04) para provocar, contra a produção, todos os tipos de falha e diagnóstico que o EdgeHealth detecta. Nada é alterado no Windows: os dispositivos são *network namespaces*, as falhas são `tc netem` e `iptables` dentro do Linux.

- `lab.sh`: lado Linux (sobe e derruba o lab, injeta falhas, roda o coletor). Executado como root no WSL.
- `edgelab.py`: lado Windows (conta de teste, dispositivos, cenários, verificações pela API, relatório). Usa só a biblioteca padrão do Python.

## Topologia

| Dispositivo | IP | Switch |
|---|---|---|
| Firewall, Servidor de arquivos, NAS, Impressora, Desktop, Sensor IoT | 10.77.0.2–.7 | `br-lab` |
| Switch andar 2, Access Point, Câmera IP, Telefone VoIP | 10.77.2.2–.5 | `br-andar2` (desligar derruba os 4) |
| DNS Cloudflare | 1.1.1.1 | internet (real) |
| Host inexistente (TEST-NET) | 192.0.2.1 | nunca responde |

Todos são medidos pelo **Coletor TESTE LAB**, que roda no WSL e envia as amostras por HTTPS para `https://marcelodomingos.pythonanywhere.com`.

## Credenciais

Ficam em `tests/lab/.credenciais-lab.json` (conta admin, Empresa B e técnico) e `tests/lab/.coletor-lab.token`, fora do Git e com acesso só do seu usuário. Os scripts nunca as mostram. Para entrar na tela como a Empresa TESTE LAB, abra o JSON localmente.

## Execução noturna (completa, sem ninguém no computador)

```powershell
cd $HOME\Documents\EdgeHealth
python tests\lab\edgelab.py noturno
```

Duração: cerca de 1h40. Deixe a janela aberta e o notebook na tomada. O script impede a suspensão por inatividade enquanto roda, mas **fechar a tampa ainda suspende**. No fim, ele restaura o lab, para o coletor e gera:

- `tests/lab/relatorio.md`: tabela com cenário, esperado, obtido, OK/FALHA e evidência, mais a lista de prints para tirar de manhã;
- `tests/lab/execucao.log`: log completo (sem senhas ou tokens);
- `tests/lab/evidencias/<data>/`: JSON da API em cada momento-chave e o ZIP exportado.

Se um passo falhar, ele registra FALHA e segue. Se o coletor cair, ele religa.

## Cenários

| # | Cenário | Como é provocado | Esperado |
|---|---|---|---|
| 1 | Saudável | — | 11 dispositivos ONLINE |
| 2 | Localizada | Impressora sem resposta | INDISPONIBILIDADE + LOCALIZADA + recomendações `local-*` |
| 3 | Compartilhada | `br-andar2` desligado | 4 falhas; COMPARTILHADA; severidade ALTA; CRITICA com 60 usuários |
| 4 | Congestionamento | NAS 250 ms + 50% perda | INSTABILIDADE + CONGESTIONAMENTO |
| 5 | Latência | Firewall 300 ms | INSTABILIDADE + LATENCIA |
| 6 | Evidência insuficiente | VoIP 50% perda, latência normal | estado EVIDENCIA_INSUFICIENTE |
| 7 | Recorrente | Sensor cai e volta 3 vezes | 3ª falha com RECORRENTE |
| 8 | Recuperação | restauração após cada cenário | encerrada por RECUPERACAO, diagnóstico preservado |
| 9 | OFFLINE permanente | 192.0.2.1 | INDISPONIBILIDADE aberta o tempo todo |
| 10 | Severidade | durações, grupo, impacto | BAIXA, MEDIA, ALTA e CRITICA (por impacto e por 60 min de duração) |
| 11 | Coletor parado | coletor parado > 240 s | coletor DESATUALIZADO, sem falhas falsas; volta a ATIVO |
| 12 | Arquivar/desarquivar | Impressora arquivada com falha aberta | ARQUIVAMENTO; desarquivada volta ONLINE com histórico |
| Extra | Coleta manual, técnico, isolamento, filtros, detalhe, exportação | API | ver relatório |

Os cenários de indisponibilidade ficam a mais de 5 min um do outro (`DIAGNOSTIC_WINDOW_SECONDS`), senão seriam correlacionados como COMPARTILHADA.

## Uso manual (apresentação ou depuração)

```powershell
python tests\lab\edgelab.py subir                      # lab + coletor em segundo plano
python tests\lab\edgelab.py status                     # lab e EdgeHealth lado a lado
python tests\lab\edgelab.py falha offline impressora   # sem resposta
python tests\lab\edgelab.py falha switch down          # derruba o andar 2 (switch up para religar)
python tests\lab\edgelab.py falha latencia firewall 300
python tests\lab\edgelab.py falha perda voip 50
python tests\lab\edgelab.py falha degradar nas 250 50
python tests\lab\edgelab.py falha restaurar todos
python tests\lab\edgelab.py falha coletor-parar        # coletor-iniciar para religar
python tests\lab\edgelab.py log                        # últimas linhas do coletor
python tests\lab\edgelab.py descer                     # para tudo e desliga o WSL
python tests\lab\edgelab.py cenario --prints --so 2,3  # cenários escolhidos, pausando para prints
```

Tempos de referência com `MONITOR_INTERVAL=60`: uma falha abre na 1ª amostra ruim (≤1 min), vira OFFLINE na 3ª (~3 min) e é encerrada após 2 amostras boas (~2 min).

## Problemas conhecidos

- **WSL desliga sozinho** quando nenhum processo está conectado. `subir` deixa um `wsl.exe` oculto ("mantenedor") e o próprio coletor roda em outro. `descer` encerra os dois.
- **Relógio**: o WSL herda o relógio do Windows ao ligar. A API recusa amostras com mais de 120 s de diferença, então `lab.sh hora` sincroniza antes de cada cenário. Mantenha o relógio do Windows sincronizado (Configurações > Hora e idioma > Sincronizar agora).
- **Certificado HTTPS no Windows**: o repositório de certificados deste Windows recusa a cadeia Let's Encrypt atual; `edgelab.py` usa o pacote de certificados do Git (`EDGEHEALTH_CA_BUNDLE` para outro caminho). A verificação continua ligada.
- **Ping sem privilégio**: `lab.sh coletor` libera `net.ipv4.ping_group_range` dentro do WSL.
