# EdgeHealth

Estrutura base do projeto EdgeHealth com backend Flask e frontend web.

## Como executar o backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Como executar o frontend

```bash
cd frontend
npm install
npm run dev
```

## Rotas

| Metodo | Rota | Descricao |
| --- | --- | --- |
| GET | `/api/health` | Verifica se a API esta online |
| POST | `/api/auth/login` | Realiza login |
| GET | `/api/dispositivos` | Lista dispositivos |
| POST | `/api/dispositivos` | Cadastra dispositivo |
| PUT | `/api/dispositivos/<id>` | Atualiza dispositivo |
| DELETE | `/api/dispositivos/<id>` | Remove dispositivo |
| POST | `/api/dispositivos/<id>/ping` | Registra ping |
| GET | `/api/metricas` | Lista metricas |
| POST | `/api/metricas` | Cadastra metrica |
