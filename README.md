# EdgeHealth

Projeto base para monitoramento de dispositivos de borda, com backend Flask, SQLAlchemy e frontend estatico.

## Estrutura

```text
backend/app/models       Modelos ORM
backend/app/services     Regras de negocio e CRUD
backend/app/controllers  Requisicoes HTTP e respostas JSON
backend/app/routes       Registro das rotas da API
frontend/src             Interface web e cliente da API
```

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

A API sobe em `http://localhost:5000`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173/public/index.html`.

## Rotas principais

| Metodo | Rota | Descricao |
| --- | --- | --- |
| GET | `/api/health` | Verifica o status da API |
| POST | `/api/database/create` | Cria as tabelas no banco configurado |
| POST | `/api/auth/register` | Cadastra usuario e empresa |
| POST | `/api/auth/login` | Autentica usuario |
| GET | `/api/dispositivos` | Lista dispositivos |
| POST | `/api/dispositivos` | Cadastra dispositivo |
| GET | `/api/dispositivos/<id>` | Detalha dispositivo |
| PATCH | `/api/dispositivos/<id>` | Atualiza dispositivo |
| DELETE | `/api/dispositivos/<id>` | Remove dispositivo |
| POST | `/api/dispositivos/<id>/ping` | Registra ping, metrica e falha |
| GET | `/api/metricas/dispositivo/<id>` | Lista metricas do dispositivo |
| POST | `/api/metricas/dispositivo/<id>` | Cadastra metrica do dispositivo |
| GET | `/api/metricas/falhas/dispositivo/<id>` | Lista falhas do dispositivo |

## Publicacao no GitHub

Depois de revisar os arquivos:

```bash
git add .
git commit -m "Adiciona estrutura inicial do EdgeHealth"
git remote add origin https://github.com/SEU_USUARIO/edgehealth.git
git push -u origin master
```
