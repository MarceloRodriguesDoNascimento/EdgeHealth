# Importação segura do banco do protótipo

A versão anterior não tinha migrations, aceitava registros sem empresa e armazenava medições simuladas. A importação não as transforma em medições verificadas. O schema novo usa outro arquivo; a origem é lida com SQLite `mode=ro` e permanece intacta.

1. Pare a aplicação antiga e guarde uma cópia consistente do banco e do `.env`. Se houver WAL, faça backup com SQLite ou encerre todas as conexões antes de copiar. O importador recusa origem com WAL pendente.
2. Instale o backend pelo README e configure **outro arquivo** no `.env`, por exemplo `DATABASE_URL=sqlite:///edgehealth-mvp.db`.
3. Dentro de `backend/`, com o ambiente virtual ativo, execute:

```bash
python -m flask --app run.py db upgrade
python -m flask --app run.py seed-catalog
python -m flask --app run.py import-legacy --source /caminho/absoluto/edgehealth-anterior.db
```

O destino deve estar vazio de empresas e importações. A importação é atômica; falha inesperada faz rollback. Não aplique a migration inicial sobre o schema antigo nem use `db stamp` para contornar incompatibilidade.

Empresas válidas são importadas. Usuários válidos mantêm vínculo com a empresa, ficam desativados e recebem hash de senha aleatória não divulgada. Dispositivos válidos aproveitam `setor` como localização quando necessário; seu status e métricas começam desconhecidos. Não se atribui empresa por aproximação.

Todos os registros de origem são preservados em `registros_legados`, com tabela, chave original, SHA-256 da fonte, resultado e motivo. Credenciais são removidas dessa cópia; o backup original permanece sob responsabilidade do operador. Órfãos, registros inválidos e observações antigas ficam em **QUARENTENA**, sem alimentar dashboard ou diagnóstico. Novos IDs podem diferir dos antigos; a referência original é mantida.

O operador local deve ativar o responsável de cada empresa importada e definir uma senha nova, solicitada sem eco no terminal:

```bash
python -m flask --app run.py activate-user --email responsavel@empresa.com.br --admin
```

Esse comando somente atua em uma conta existente, revoga sessões e não troca seu vínculo com a empresa. Não passe senha como argumento de linha de comando.

Para revisar registros e exceções:

```bash
python -m flask --app run.py export-legacy --output revisao-legado.jsonl
```

O arquivo deve ser novo: o comando não sobrescreve arquivos existentes. Essa exportação local é administrativa, abrange os registros da importação e deve receber as mesmas permissões do backup. Não é exposta por API. Após validação humana, dados inválidos podem ser recadastrados pela interface sem alterar a cópia de origem.

Os bancos anteriormente versionados continuam recuperáveis no commit base `fc60d981e783270e3d6caeed72f88bd1d9e91029`. Não restaure tabelas antigas sobre o banco novo.
