# EdgeHealth

Estrutura base do projeto EdgeHealth com backend Flask e frontend web.

EdgeHealth, um sistema de monitoramento e diagnóstico lógico de redes.

O problema que queremos resolver é a dificuldade que pequenas e médias empresas têm para identificar rapidamente falhas, instabilidades e dispositivos indisponíveis em suas redes de computadores. Muitas vezes, quando a rede apresenta problema, a identificação da causa é feita manualmente, o que pode demorar e prejudicar o funcionamento da empresa.

A nossa solução é um sistema que permite cadastrar dispositivos de rede, como roteadores, switches, servidores e computadores, acompanhando o status de cada um deles. O EdgeHealth realiza verificações lógicas de conectividade, como testes de resposta, análise de latência e perda de pacotes, sem depender de sensores físicos conectados aos cabos ou equipamentos.

Com base nessas informações, o sistema classifica os dispositivos como online, instável ou offline. Além disso, ele compara os dispositivos afetados para indicar a possível origem do problema. Por exemplo, se apenas um dispositivo falhar, o problema pode estar nele. Se vários dispositivos de uma mesma área falharem, o problema pode estar em um switch ou ponto da rede. Se todos os dispositivos caírem, pode ser uma falha geral na infraestrutura.

O sistema também registra o histórico de falhas, apresenta as informações em um dashboard com gráficos e indicadores, e pode estimar o impacto financeiro causado pelo tempo em que a rede ficou indisponível.

Com isso, o EdgeHealth busca ajudar empresas e equipes técnicas a identificarem problemas de rede de forma mais rápida, organizada e visual, reduzindo o tempo de diagnóstico e facilitando a tomada de decisão.

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
