# Coletor remoto EdgeHealth

O coletor roda **dentro da rede da empresa**. Ele mede os dispositivos atribuídos a ele na interface (ICMP: pacotes enviados/recebidos e latência) e envia as amostras ao EdgeHealth hospedado por **HTTPS**. Usa somente conexões de saída; nenhuma porta de entrada é aberta na rede e nenhum equipamento é exposto à Internet.

O coletor **não decide** status, falhas, severidade ou diagnóstico. Essas regras ficam no servidor, no mesmo pipeline do worker local.

## Como funciona

1. A cada 30 s (ou no intervalo configurado no servidor, se menor), busca `GET /api/coletor/configuracao`: lista de dispositivos, intervalo, pacotes e timeout.
2. Mede os dispositivos vencidos, com concorrência limitada (`--workers`, padrão 4).
3. Grava cada amostra em uma fila local em disco (`--queue-file`), limitada (`--max-queue`, padrão 5000; as mais antigas são descartadas primeiro).
4. Envia em lotes (`POST /api/coletor/amostras`). Cada amostra tem um UUID. Reenvios são idempotentes: o servidor responde `DUPLICADA` e não grava de novo.
5. Se a API estiver indisponível, continua medindo e guarda na fila. As novas tentativas usam backoff exponencial de 2 s a 300 s, com variação aleatória.
6. Envia heartbeat com a versão e o tamanho da fila. Sem contato por `COLLECTOR_STALE_SECONDS` (padrão 180 s), a interface mostra o coletor como **Sem contato recente**. Isso indica falta de dados, não queda de dispositivos.
7. Sem permissão para ICMP, envia o erro `PERMISSAO_ICMP`. O dispositivo exibe o erro, sem amostra, sem OFFLINE e sem falha.

Respostas do servidor por amostra: `ACEITA`, `DUPLICADA`, `ATRASADA` (mais antiga que a última processada: entra no histórico sem mudar o estado nem reabrir ocorrência), `REJEITADA` (inválida ou dispositivo não atribuído) e `TENTAR_NOVAMENTE` (o dispositivo está sendo processado; a amostra permanece na fila).

## 1. Criar a credencial

Na interface, como administrador: **Coletores → Cadastrar coletor**. Copie a credencial (`ehc_...`). **Ela é exibida uma única vez.** O servidor guarda somente o hash.

Depois, em **Dispositivos → Editar → Origem da medição**, escolha o coletor para cada dispositivo da rede privada.

## 2. Instalar — Windows (PowerShell)

Requer Python 3.12 ou superior. Abra o PowerShell **na pasta `collector` do repositório** e confira com `Get-Location` que o caminho termina em `\collector`. Se o ZIP foi extraído em uma pasta dentro de outra com o mesmo nome, entre na pasta que contém `edgehealth_collector.py`.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Espere a instalação terminar sem erros. Depois, salve a credencial em um arquivo com acesso restrito ao seu usuário. Substitua o texto entre aspas pela credencial copiada:

```powershell
Set-Content -Path .\coletor.token -Value "COLE_AQUI_A_CREDENCIAL" -NoNewline -Encoding ascii
icacls .\coletor.token /inheritance:r /grant:r "$($env:USERNAME):(R,W)"
```

Teste um ciclo. Use o endereço real da sua hospedagem; o domínio abaixo é só exemplo:

```powershell
python edgehealth_collector.py --api-url https://edgehealth.exemplo.org --token-file .\coletor.token --once
```

Execução contínua: `python edgehealth_collector.py --api-url https://edgehealth.exemplo.org --token-file .\coletor.token`. Para iniciar com o Windows, crie uma tarefa no **Agendador de Tarefas** ("Ao iniciar o sistema") que execute `.\.venv\Scripts\python.exe` com esses argumentos, na pasta `collector`.

No Windows 11 deste projeto, o ICMP funcionou sem privilégios de administrador. A latência medida tem granularidade de cerca de 0,5 ms. Um equipamento na mesma LAN pode aparecer com `0` ms, o mesmo que o `ping` do sistema mostra como `<1ms`.

## 2. Instalar — Linux (bash)

```bash
cd collector                # pasta que contém edgehealth_collector.py
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
install -m 600 /dev/null coletor.token && nano coletor.token   # cole a credencial e salve
python edgehealth_collector.py --api-url https://edgehealth.exemplo.org --token-file coletor.token --once
```

O ICMP sem privilégios no Linux depende de `net.ipv4.ping_group_range`. Se aparecer `PERMISSAO_ICMP`, o administrador da máquina deve incluir o grupo do usuário do serviço nesse intervalo, por exemplo `sudo sysctl -w net.ipv4.ping_group_range="0 2147483647"`, e persistir em `/etc/sysctl.d/`. Não execute o coletor como root.

Exemplo de serviço systemd (`/etc/systemd/system/edgehealth-collector.service`; ajuste o usuário e os caminhos reais):

```ini
[Unit]
Description=EdgeHealth collector
After=network-online.target
[Service]
User=edgehealth
WorkingDirectory=/opt/edgehealth/collector
ExecStart=/opt/edgehealth/collector/.venv/bin/python edgehealth_collector.py --api-url https://edgehealth.exemplo.org --token-file /opt/edgehealth/collector/coletor.token
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
```

## Opções

| Opção | Variável | Padrão |
|---|---|---|
| `--api-url` | `EDGEHEALTH_API_URL` | obrigatório; HTTPS (HTTP somente para `localhost`) |
| `--token-file` | `EDGEHEALTH_COLLECTOR_TOKEN_FILE` | ou a credencial em `EDGEHEALTH_COLLECTOR_TOKEN` |
| `--queue-file` | `EDGEHEALTH_QUEUE_FILE` | `edgehealth-fila.jsonl` |
| `--max-queue` | `EDGEHEALTH_MAX_QUEUE` | 5000 (100–100000) |
| `--workers` | `EDGEHEALTH_WORKERS` | 4 (1–16) |
| `--once` | — | executa um ciclo e encerra |
| `--allow-http` | — | somente laboratório, sem TLS |

## Operação

- **Atualizar o coletor:** pare o serviço, substitua `edgehealth_collector.py`, reinstale `requirements.txt` e inicie. A fila em disco é preservada.
- **Credencial perdida ou exposta:** em **Coletores**, use **Nova credencial**: a anterior para de funcionar imediatamente. Para desativar de vez, use **Revogar**.
- **Credencial inválida ou revogada:** o coletor encerra com código 2 e registra a mensagem no log, sem a credencial.
- **Relógio:** mantenha o NTP ativo. O servidor rejeita amostras com horário mais de 120 s no futuro e mais antigas que 24 h. O coletor avisa quando a diferença para o servidor passa de 60 s.
- **Um coletor por dispositivo:** o worker local do servidor nunca mede dispositivos atribuídos a um coletor. O mesmo lease por dispositivo serializa as ingestões.
- O coletor mede somente os endereços cadastrados. Não há descoberta ou varredura de rede.
