# Perguntas prováveis na arguição — EdgeHealth

25 perguntas que o professor provavelmente fará, com uma resposta curta baseada no código real. **Não decorem**: entendam a ideia e respondam com as próprias palavras. Os caminhos são a partir da raiz do repositório.

## Arquitetura em camadas

**1. Como a API está organizada?**
Em quatro camadas, cada uma numa pasta de `backend/`: `controllers/` recebe a requisição HTTP, `services/` aplica as regras (um caso de uso por classe), `models/` mapeia as tabelas e faz o CRUD, e `repositories/` tem as consultas SQL especiais. O fluxo é sempre Tela → Controller → Service → Model/Repository → Banco. O `backend/tests/test_architecture.py` falha se alguma camada for pulada.

**2. O que um Controller faz e o que ele não pode fazer?**
Ele lê o JSON, a query string e o usuário logado, chama **um único** Service e devolve a resposta com o status HTTP (`backend/controllers/base_controller.py`). Não tem regra de negócio e não acessa o banco: o teste de arquitetura falha se um controller importar `db`/`sqlalchemy` ou chamar mais de um Service.

**3. E o Service?**
É onde ficam as regras. Cada classe é um caso de uso com o método `executar()`, por exemplo `CadastrarDispositivoService` ou `RegistrarImpactoService` (`backend/services/falhas/registrar_impacto_service.py`). Ele valida os dados, coordena models e repositories e confirma a transação. Não lê `flask.request` nem escreve SQL; recebe usuário e empresa como parâmetros.

**4. Qual a diferença entre Model e Repository?**
O Model é a tabela com o CRUD básico herdado do `BaseModel` (`backend/models/base.py`): `salvar`, `atualizar`, `deletar`, `listar_todos`, `buscar_por_id`. O Repository é só para consultas especiais, que não são um simples "buscar por id": filtros com paginação, agregações, rankings, consultas multiempresa.

**5. Por que o Repository não repete o CRUD?**
Porque o CRUD já está na classe base de todos os models. Repetir em cada repository seria duplicação e deixaria dois caminhos para a mesma operação. Assim cada camada tem uma responsabilidade só: o model sabe salvar a si mesmo; o repository sabe fazer as consultas difíceis, como `FalhaRepository.historico` ou `RankingCustoRepository.top_dispositivos`.

**6. Por que um Service por caso de uso, e não um "FalhaService" com tudo?**
Para cada classe ter um motivo só para mudar (o S do SOLID). Se mudar a regra do impacto, só o `RegistrarImpactoService` muda; a listagem (`ListarFalhasService`) e a explicação com IA (`ExplicarFalhaComIaService`) ficam intactas. Também fica fácil achar o código: o nome da classe é o caso de uso.

**7. Onde o SOLID aparece no projeto?**
- **S**: um caso de uso por Service; a única classe que fala com o Gemini é o `GeminiService`.
- **O/L**: todos os models herdam do `BaseModel` e ganham o CRUD sem mudar a base; qualquer model funciona onde se espera um `BaseModel`.
- **I**: o `BaseController` só tem o que todo controller usa (ler payload, parâmetro, usuário, resposta).
- **D**: o `ExplicarFalhaComIaService` recebe o `GeminiService` no construtor e o `GeminiService` recebe o transporte HTTP; nos testes passamos versões falsas, sem internet (`backend/tests/test_ia.py`).
Sejam honestos: as regras do diagnóstico ficam numa sequência de `if` no `AnalisarFalhaService`; uma regra nova exige editar essa classe.

## Cliente-servidor

**8. Por que dá para dizer que é cliente-servidor?**
O frontend (`frontend/`, Vite) e a API (`backend/`, Flask) são aplicações separadas. Em desenvolvimento rodam em dois servidores, Vite na porta 5173 e Flask na 5000, e o frontend só fala com a API por HTTP com JSON (`frontend/src/services/api.js`, função `apiFetch` com `fetch`). O coletor é um terceiro cliente da mesma API. A prova com comandos está no README, seção "Cliente-servidor".

**9. Mas em produção o Flask serve o frontend. Continua cliente-servidor?**
Sim. O Flask só entrega os arquivos estáticos do build (`npm run build`); depois, o código roda no navegador e chama a API por `fetch`, como em desenvolvimento. Servir na mesma origem evita liberar CORS e mantém o cookie de sessão protegido.

## Diagrama, banco e SQL

**10. O diagrama de classes corresponde ao sistema?**
Sim: ele é gerado a partir dos models por `docs/gerar_diagrama_classes.py`, e o `backend/tests/test_diagram.py` falha se uma classe, atributo ou relação do diagrama for diferente do código. São 13 entidades; a Empresa tem usuários, coletores e dispositivos; o dispositivo tem métricas e falhas; a falha tem impacto e diagnóstico.

**11. Por que SQLite?**
É um arquivo só, sem servidor de banco, o que cabe no plano gratuito do PythonAnywhere e numa instância única. O esquema é versionado com migrations do Alembic, e o `backend/database/create_database.sql` cria o banco inteiro (o `test_database_script.py` garante que ele bate com as migrations).

**12. Onde estão as stored procedures?**
O SQLite não tem stored procedures. Por isso as consultas especiais ficam nos Repositories, em SQL escrito à mão com `text()` e parâmetros nomeados (ex.: `FalhaRepository.ranking_dispositivos`, com `JOIN`, `GROUP BY`, `ORDER BY`, `LIMIT`) ou em SQLAlchemy Core. Todas são testadas com o resultado exato em `backend/tests/test_repositories.py`.

**13. Como uma empresa é impedida de ver os dados de outra?**
Toda busca por id passa por um `buscar_da_empresa` no repository, que faz `JOIN` até `dispositivos.empresa_id` com a empresa da sessão (ex.: `backend/repositories/falha_repository.py`). Se o id é de outra empresa, a resposta é **404**, como se não existisse. O `empresa_id` nunca vem do cliente.

## Regras do domínio

**14. Como o sistema decide que um equipamento caiu?**
Pelas amostras do coletor, processadas no servidor pelo `RegistrarMedicaoService` (`backend/services/monitoramento/`). Uma amostra ruim já abre a ocorrência como instabilidade; três amostras seguidas sem resposta confirmam OFFLINE; duas amostras boas confirmam a recuperação e encerram a ocorrência. O coletor só mede; quem decide é sempre o servidor.

**15. Como o diagnóstico decide a causa provável?**
Por regras, no `AnalisarFalhaService` (`backend/services/diagnosticos/analisar_falha_service.py`), olhando as amostras dos últimos 5 minutos, os outros dispositivos e o histórico de 7 dias:
- **LOCALIZADA**: o equipamento está OFFLINE e outros da empresa estão ONLINE.
- **COMPARTILHADA**: dois ou mais equipamentos ficaram indisponíveis na mesma janela.
- **CONGESTIONAMENTO**: latência e perda acima dos limites; **LATENCIA**: só latência alta.
- **RECORRENTE**: pelo menos duas outras ocorrências nos últimos 7 dias.
Sem evidência, o estado é "evidência insuficiente". As recomendações vêm do catálogo por regra (`DiagnosticoRepository.recomendacoes_das_regras`). São hipóteses, não certezas.

**16. E a severidade?**
`CalcularSeveridadeService` usa o maior nível que se aplica: indisponibilidade confirmada ou 5 minutos já é MEDIA; 15 minutos, 3 dispositivos relacionados ou 10 pessoas afetadas é ALTA; 60 minutos ou 50 pessoas é CRITICA. Os limites estão em `backend/app/config.py`, e o motivo fica salvo junto com a severidade.

**17. Como o prejuízo é calculado?**
Em `CalculadoraPrejuizo` (`backend/services/custos/calculadora_prejuizo.py`): horas de expediente dentro da falha × (pessoas afetadas × custo por hora × % de perda de produtividade + receita por hora do dispositivo) + custos diretos. O custo por hora é salário médio × fator de encargos ÷ horas por mês. Só conta o horário de expediente da empresa; numa queda compartilhada, as mesmas pessoas não são contadas duas vezes. O dinheiro é `Decimal`, nunca `float`, e a tela mostra a conta aberta.

**18. De onde vem o número de pessoas afetadas?**
Na ordem: o que a equipe informou na ocorrência; senão, o cadastro do dispositivo; senão, um padrão pelo tipo de equipamento (`CalculadoraPrejuizo.parametros`). A tela diz qual foi a origem.

## Segurança e LGPD

**19. Como as senhas e a sessão são protegidas?**
Senhas com hash pelo Werkzeug (`generate_password_hash`, em `backend/services/autenticacao/`). A sessão é um token aleatório num cookie HttpOnly com SameSite, e o banco guarda só o hash do token. Toda alteração exige o cabeçalho CSRF (`backend/app/security.py`). O login é limitado a 10 tentativas em 15 minutos (`LOGIN_MAX_ATTEMPTS` em `config.py`).

**20. E a credencial do coletor?**
É gerada como `ehc_` + token aleatório (`backend/services/coletores/credencial_coletor.py`), mostrada uma única vez e guardada só como hash SHA-256. O coletor manda no cabeçalho `Authorization: Bearer`; o administrador pode rotacionar ou revogar.

**21. O que vocês fazem para a LGPD?**
Termos de Uso e Aviso de Privacidade com aceite obrigatório e versão registrada (403 até aceitar, em `ValidarSessaoService`); retenção das amostras por 180 dias (`flask purge-history`); anonimização de um usuário a pedido (`flask anonymize-user`); e a IA recebe só dados técnicos. O inventário de dados e os operadores (Google e PythonAnywhere) estão em `docs/LGPD.md`.

## IA e hospedagem

**22. Como a IA está integrada?**
Como serviço, encapsulada: o `GeminiService` (`backend/services/ia/gemini_service.py`) é a única classe que chama a API do Gemini, por HTTPS, com a chave no cabeçalho e timeout de 20 s. O `ExplicarFalhaComIaService` monta o pedido a partir do diagnóstico que o sistema já calculou. A chave fica só no `.env` do servidor, nunca no Git.

**23. Que dados vão para o Gemini? E se a IA errar?**
Só uma lista permitida de dados técnicos (`ExplicarFalhaComIaService.contexto`): tipo da ocorrência, severidade, horários, tipo e local do dispositivo, causas, recomendações e prejuízo. Nunca nomes, e-mails, CNPJ, IP ou nome da empresa; o `test_ia.py` verifica isso. A IA só explica: ela é instruída a não contradizer o diagnóstico, a resposta vem com o aviso "confira antes de agir", e o diagnóstico por regras não muda. Há limite de 10 explicações por hora por empresa, e os erros viram mensagens claras (503/502/429).

**24. Como funciona a hospedagem?**
No PythonAnywhere, plano gratuito: o Flask roda como app WSGI e serve a API e o build do frontend em <https://marcelodomingos.pythonanywhere.com>, com HTTPS obrigatório e cabeçalhos de segurança (HSTS, CSP). O plano não tem processo permanente, mas não precisa: quem mede é o coletor na rede da empresa, e o servidor só processa. Detalhes em `docs/PYTHONANYWHERE.md`.

**25. Como vocês sabem que tudo funciona?**
São 186 testes automatizados no backend (mais 3 opcionais de rede real) e 20 no frontend. Eles cobrem regras, isolamento entre empresas, coletor, IA sem internet e telas. Há também testes que conferem a própria documentação: README (`test_readme.py`), fluxogramas (`test_flowcharts.py`), diagrama (`test_diagram.py`) e banco (`test_database_script.py`).
