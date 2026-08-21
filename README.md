# EdgeHealth

## Funcionalidades Implementadas

1. Login do usuário
2. Cadastro de empresa
3. Listagem de empresas
4. Atualização de empresa
5. Exclusão de empresa
6. Cadastro de dispositivo
7. Listagem de dispositivos
8. Atualização de dispositivo
9. Exclusão de dispositivo
10. Registro de ping e status do dispositivo

Sistema de monitoramento e diagnóstico lógico de redes para pequenas e médias empresas.

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
| GET | `/api/dispositivos/<id>` | Busca dispositivo |
| POST | `/api/dispositivos` | Cadastra dispositivo |
| PUT | `/api/dispositivos/<id>` | Atualiza dispositivo |
| DELETE | `/api/dispositivos/<id>` | Remove dispositivo |
| POST | `/api/dispositivos/<id>/ping` | Registra ping |
| GET | `/api/empresas` | Lista empresas |
| GET | `/api/empresas/<id>` | Busca empresa |
| POST | `/api/empresas` | Cadastra empresa |
| PUT | `/api/empresas/<id>` | Atualiza empresa |
| DELETE | `/api/empresas/<id>` | Remove empresa |
| GET | `/api/metricas` | Lista metricas |
| GET | `/api/metricas/<id>` | Busca metrica |
| POST | `/api/metricas` | Cadastra metrica |
| PUT | `/api/metricas/<id>` | Atualiza metrica |
| DELETE | `/api/metricas/<id>` | Remove metrica |
| GET | `/api/falhas` | Lista historico de falhas |
| GET | `/api/falhas/<id>` | Busca falha |
| POST | `/api/falhas` | Registra falha |
| PUT | `/api/falhas/<id>` | Atualiza falha |
| DELETE | `/api/falhas/<id>` | Remove falha |
