# Hospedagem gratuita no PythonAnywhere (demonstração acadêmica)

Plano **Beginner (gratuito)**: nenhuma cobrança, nenhum cartão, nenhum trial pago. É um ambiente para a **demonstração escolar**, não para operação em produção (seção 6).

Estado: **preparado; ainda não implantado.** Os resultados da implantação ficam registrados na seção 7.

## 1. Compatibilidade verificada (documentação oficial, 06/10/2026)

| Requisito do EdgeHealth | Plano gratuito | Situação |
|---|---|---|
| Python 3.12 e dependências | Contas novas têm Python 3.11, 3.12 e 3.13 ([versões](https://help.pythonanywhere.com/pages/PythonVersions/)). As dependências de execução (`backend/requirements.txt`) vêm do PyPI | ✅ |
| Flask por WSGI | Configuração manual com arquivo WSGI e virtualenv ([Flask](https://help.pythonanywhere.com/pages/Flask/)). `run.py` não chama `app.run()` na importação | ✅ (validado localmente com o mesmo `wsgi.py`) |
| Frontend compilado | O build é gerado localmente e enviado como ZIP. O Flask serve `index.html` e as páginas legais; `/assets/` pode ser mapeado como arquivo estático | ✅ |
| SQLite privado e persistente | Arquivo em `/home/USUARIO/edgehealth-data/`, fora do repositório e do diretório web. O disco fica em sistema de arquivos de rede: o SQLite é mais lento e bloqueia o banco inteiro a cada escrita ([bancos](https://help.pythonanywhere.com/pages/KindsOfDatabases/), [lentidão](https://help.pythonanywhere.com/pages/MySiteIsSlow/)) | ✅ para demonstração, com limites (seção 4) |
| HTTPS e cookies | HTTPS no subdomínio `USUARIO.pythonanywhere.com`, com opção **Force HTTPS** ([HTTPS](https://help.pythonanywhere.com/pages/ForcingHTTPS/)). Com `COOKIE_SECURE=true`, os cookies saem com `Secure` independentemente do esquema visto pelo app | ✅ |
| IP real do cliente (limite de login) | O IP real chega no fim de `X-Forwarded-For` e em `X-Real-IP`; `REMOTE_ADDR` é o balanceador ([IPs](https://help.pythonanywhere.com/pages/WebAppClientIPAddresses/)). `TRUST_PROXY=1` usa o último item de `X-Forwarded-For` | ✅ (conferir após a implantação) |
| Recebimento das medições do coletor | O coletor faz requisições **de entrada** HTTPS para o app. A restrição de internet de saída do plano gratuito não se aplica a isso | ✅ (validar após a implantação) |
| Cota de CPU | "It does not currently apply to your web apps" ([CPU seconds](https://help.pythonanywhere.com/pages/WhatAreCPUSeconds/)). Os 100 s/dia valem só para consoles; comandos de manutenção são curtos | ✅ |
| Concorrência | **1 web worker** ([plano gratuito](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/)): as requisições são atendidas uma por vez. O lease por dispositivo e as transações curtas não dependem de paralelismo | ✅ com poucos usuários e poucos dispositivos |
| Armazenamento | 512 MiB | ✅ (virtualenv de runtime + código + banco com retenção de 30 dias) |
| Worker permanente e tarefas agendadas | Não disponíveis para contas criadas a partir de 15/01/2026 ([mudanças](https://blog.pythonanywhere.com/221/)) | ✅ não são necessários: o monitoramento é feito pelo **coletor local**, e o processamento ocorre na API |
| Docker | Indisponível | ✅ não usado |
| Expiração | O web app expira após **1 mês** sem renovação. Nada é apagado: basta clicar no botão de extensão na aba **Web** ([expirações](https://blog.pythonanywhere.com/129)) | ⚠️ exige ação mensal (seção 5) |

**Conclusão:** o plano gratuito comporta a demonstração. Não encontrei nenhum bloqueio que exija mudar o código.

## 2. Arquivos preparados

- `deploy/pythonanywhere/wsgi.py`: ponto de entrada WSGI.
- `deploy/pythonanywhere/env.pythonanywhere.example`: configuração da demonstração (sem segredos).
- `deploy/pythonanywhere/edgehealth-frontend-dist.zip`: build do frontend, gerado localmente com `npm run build`. Não vai para o Git; gere de novo após mudanças na interface (seção 8).

## 3. Passo a passo

**Nunca cole senhas ou credenciais de coletor em conversas, e-mails ou commits.**

### 3.1 Criar a conta (você)

1. Acesse https://www.pythonanywhere.com/pricing/ e escolha **Create a Beginner account** (gratuita).
2. O nome de usuário define o endereço público: `https://USUARIO.pythonanywhere.com`.
3. Confirme o e-mail. **Não** informe dados de pagamento e não clique em upgrade.

### 3.2 Enviar o frontend compilado (você)

Na aba **Files**, na pasta `/home/USUARIO/`, use **Upload a file** e envie:

`C:\Users\marce\Documents\EdgeHealth\deploy\pythonanywhere\edgehealth-frontend-dist.zip`

### 3.3 Instalar (você, em um console Bash do PythonAnywhere)

Em **Consoles → Bash**, cole **um bloco por vez** e espere cada um terminar:

```bash
cd ~
git clone --branch feat/edgehealth-mvp https://github.com/MarceloRodriguesDoNascimento/EdgeHealth.git
mkdir -p ~/edgehealth-data ~/EdgeHealth/frontend/dist
unzip -o ~/edgehealth-frontend-dist.zip -d ~/EdgeHealth/frontend/dist
ls ~/EdgeHealth/frontend/dist        # deve listar: assets index.html legal.css privacidade.html termos.html
```

```bash
mkvirtualenv --python=/usr/bin/python3.12 edgehealth
pip install -r ~/EdgeHealth/backend/requirements.txt
```

Espere o `pip` terminar sem erros antes de continuar. Se o console fechar, reative o ambiente com `workon edgehealth`.

```bash
sed "s/SEU_USUARIO/$USER/g" ~/EdgeHealth/deploy/pythonanywhere/env.pythonanywhere.example > ~/EdgeHealth/backend/.env
cd ~/EdgeHealth/backend
python -m flask --app run.py db upgrade
python -m flask --app run.py seed-catalog
python -m flask --app run.py db check
du -sh ~/.virtualenvs/edgehealth ~/EdgeHealth ~/edgehealth-data
```

`db check` deve responder "No new upgrade operations detected".

### 3.4 Criar o web app (você, na aba Web)

1. **Add a new web app** → aceite o domínio `USUARIO.pythonanywhere.com` → **Manual configuration** → **Python 3.12**.
2. Em **Virtualenv**, informe `/home/USUARIO/.virtualenvs/edgehealth`.
3. No console Bash, grave o WSGI (substitui o arquivo de exemplo do PythonAnywhere):

   ```bash
   sed "s/SEU_USUARIO/$USER/g" ~/EdgeHealth/deploy/pythonanywhere/wsgi.py > /var/www/${USER}_pythonanywhere_com_wsgi.py
   ```

4. Em **Static files**, adicione a URL `/assets/` com o diretório `/home/USUARIO/EdgeHealth/frontend/dist/assets`.
5. Ative **Force HTTPS**.
6. Clique em **Reload**.

### 3.5 Primeiro acesso e coletor (você)

1. Abra `https://USUARIO.pythonanywhere.com`, cadastre a empresa e aceite os Termos.
2. Em **Coletores**, cadastre "Coletor do notebook" e **copie a credencial**.
3. No Windows, salve a credencial **sem mostrá-la a ninguém**. No PowerShell, na pasta `collector`:

   ```powershell
   Set-Content -Path .\coletor-hospedado.token -Value "COLE_AQUI_A_CREDENCIAL" -NoNewline -Encoding ascii
   icacls .\coletor-hospedado.token /inheritance:r /grant:r "$($env:USERNAME):(R,W)"
   ```

4. Cadastre os dispositivos com **Origem da medição: Coletor do notebook**.
5. Inicie o coletor, na pasta `collector`, com a venv do coletor ou a do backend:

   ```powershell
   python edgehealth_collector.py --api-url https://USUARIO.pythonanywhere.com --token-file .\coletor-hospedado.token
   ```

## 4. Limites para a demonstração

| Item | Valor | Motivo |
|---|---|---|
| Dispositivos | até 5 | 1 worker e SQLite em disco de rede |
| `MONITOR_INTERVAL` | 60 s | cerca de 1 lote por minuto por coletor |
| Coletores | 1–2 | — |
| Usuários simultâneos | poucos | o dashboard consulta a API a cada 15 s por navegador aberto |
| Retenção (`METRIC_RETENTION_DAYS`) | 30 dias | 5 dispositivos × 1 amostra/min geram cerca de 7.200 linhas/dia; o banco fica bem abaixo de 512 MiB |

## 5. Rotina de operação no plano gratuito

- **Renovação mensal:** o PythonAnywhere envia um e-mail antes da expiração. Entre na aba **Web** e clique no botão de extensão (*Run until 1 month from today*). **Uma conta criada em 06/10/2026 expira por volta de 06/11/2026, véspera da apresentação de 07/11: renove na semana da apresentação.**
- **Backup** (sem tarefas agendadas, é manual). Em um console Bash:

  ```bash
  workon edgehealth && cd ~/EdgeHealth/backend
  python -m flask --app run.py backup --output ~/edgehealth-data/backup-$(date +%Y%m%d-%H%M).db
  ```

  Baixe o arquivo pela aba **Files** e apague a cópia no servidor para economizar espaço. O backup contém dados pessoais: guarde-o com acesso restrito.
- **Retenção** (manual, semanal): `python -m flask --app run.py purge-history --dry-run` e depois `python -m flask --app run.py purge-history`.
- **Atualizar a aplicação:**
  1. Faça o backup.
  2. `cd ~/EdgeHealth && git pull`.
  3. Se a interface mudou, envie um novo ZIP e descompacte.
  4. `pip install -r backend/requirements.txt`.
  5. `python -m flask --app run.py db upgrade`.
  6. **Reload** na aba Web.
- **Logs:** na aba **Web**, *error log* e *server log*. Eles não contêm senhas, tokens nem cookies.

## 6. Demonstração acadêmica × produção

| Aspecto | Esta demonstração (gratuita) | Produção |
|---|---|---|
| Disponibilidade | Expira em 1 mês sem renovação; sem SLA; sem suporte direto | Serviço contínuo com monitoramento e SLA |
| Banco | SQLite em disco de rede, 1 worker | SQLite em disco local com uma instância, ou PostgreSQL gerenciado |
| Rotinas | Backup e retenção manuais | Agendadas, com backup externo criptografado |
| Domínio | `USUARIO.pythonanywhere.com` | Domínio próprio |
| Escala | Até 5 dispositivos e poucos usuários | Dimensionada pela carga |
| Privacidade | Dados de teste da equipe; provedor registrado em `LGPD.md` §6 quando a conta existir | Contrato com operador, avaliação de transferência internacional, controlador e encarregado definidos |

## 7. Resultados da implantação

Pendente: ainda não foi realizada.

## 8. Regerar o ZIP do frontend (Windows, PowerShell, na raiz do repositório)

```powershell
cd frontend; npm run build; cd ..
.\backend\.venv\Scripts\python.exe -I -c "import sys,zipfile,pathlib; r=pathlib.Path(sys.argv[1]); z=zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED); [z.write(p,p.relative_to(r).as_posix()) for p in sorted(r.rglob('*')) if p.is_file()]; z.close()" frontend\dist deploy\pythonanywhere\edgehealth-frontend-dist.zip
```

Use esse comando, e não o `Compress-Archive`: no Windows PowerShell 5.1, ele grava os caminhos com `\`, que o `unzip` do Linux não interpreta como pastas.
