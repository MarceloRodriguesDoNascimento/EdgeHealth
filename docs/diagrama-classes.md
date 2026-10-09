# Diagrama de classes do domínio

Gerado a partir dos Models reais em [`backend/models/`](../backend/models) por
[`docs/gerar_diagrama_classes.py`](gerar_diagrama_classes.py); `backend/tests/test_diagram.py` falha se o
diagrama ficar diferente do código. Imagem para slides: [`docs/img/diagrama-classes.svg`](img/diagrama-classes.svg)
([PNG](img/diagrama-classes.png)).

- **13 entidades**, todas herdando de `BaseModel` (`db.Model` do Flask-SQLAlchemy), que concentra o CRUD
  exigido pela disciplina: `salvar()`, `atualizar()`, `deletar()`, `listar_todos()` e `buscar_por_id()`
  (`$` = método de classe). Consultas especiais ficam na camada Repository.
- Atributos com o tipo do código (`Decimal` = valor monetário exato, `json` = coluna JSON). `PK` = chave primária,
  `FK` = chave estrangeira.

```mermaid
classDiagram
    direction TB
    class BaseModel {
        <<abstract>>
        +salvar(commit) BaseModel
        +atualizar(commit, campos) BaseModel
        +deletar(commit) None
        +listar_todos()$ list
        +buscar_por_id(id)$ BaseModel
        +buscar_um_por(filtros)$ BaseModel
    }
    class Empresa {
        +int id PK
        +str nome_fantasia
        +str cnpj
        +str email
        +str telefone
        +datetime criada_em
        +Decimal salario_medio
        +Decimal fator_encargos
        +int horas_mes
        +int total_funcionarios
        +str expediente_dias
        +str expediente_inicio
        +str expediente_fim
        +str fuso
        +str assistente_custos
    }
    class Usuario {
        +int id PK
        +int empresa_id FK
        +str nome
        +str email
        +str senha_hash
        +str papel
        +bool ativo
        +datetime criada_em
        +str termos_versao
        +datetime termos_aceitos_em
        +datetime anonimizado_em
    }
    class AuthSession {
        +str id PK
        +int usuario_id FK
        +str csrf_hash
        +datetime expires_at
    }
    class LoginAttempt {
        +int id PK
        +str key
        +datetime created_at
    }
    class Coletor {
        +int id PK
        +int empresa_id FK
        +str nome
        +str token_hash
        +str token_prefixo
        +datetime criado_em
        +datetime rotacionado_em
        +datetime revogado_em
        +datetime ultimo_contato
        +str versao
        +int fila_pendente
        +str ultimo_erro
        +datetime ultimo_erro_em
        +datetime janela_inicio
        +int janela_requisicoes
    }
    class Dispositivo {
        +int id PK
        +int empresa_id FK
        +int coletor_id FK
        +str nome
        +str ip
        +str tipo
        +str localizacao
        +str status
        +datetime ultima_coleta
        +float latencia_ms
        +float perda_pacotes_pct
        +int falhas_consecutivas
        +int sucessos_consecutivos
        +datetime arquivado_em
        +datetime criado_em
        +str erro_coleta
        +str lease_owner
        +datetime lease_until
        +datetime proxima_coleta
        +int usuarios_dependentes
        +int perda_produtividade_pct
        +Decimal receita_hora_dependente
        +em_coleta(agora)
        +reiniciar_estado()
    }
    class Metrica {
        +int id PK
        +int dispositivo_id FK
        +datetime coletada_em
        +bool respondeu
        +float latencia_ms
        +int pacotes_enviados
        +int pacotes_recebidos
        +float perda_pacotes_pct
        +str status
        +int coletor_id FK
        +str amostra_uid
        +datetime recebida_em
        +bool fora_de_ordem
    }
    class Falha {
        +int id PK
        +int dispositivo_id FK
        +str tipo
        +str estado
        +datetime inicio
        +datetime fim
        +datetime ultima_observacao
        +str descricao
        +str severidade
        +json justificativa
        +str encerramento
        +encerrar(quando, motivo)
    }
    class Impacto {
        +int id PK
        +int falha_id FK
        +int usuarios_afetados
        +str origem
        +str observacao
        +datetime atualizado_em
        +Decimal custos_diretos
    }
    class Diagnostico {
        +int id PK
        +int falha_id FK
        +str descricao
        +json causas
        +json evidencias
        +str estado
        +datetime analisado_em
        +str versao_regras
    }
    class Recomendacao {
        +int id PK
        +str regra
        +str codigo
        +str titulo
        +str acao
    }
    class DiagnosticoRecomendacao {
        +int diagnostico_id PK FK
        +int recomendacao_id PK FK
    }
    class RegistroLegado {
        +int id PK
        +str fonte_sha256
        +str tabela
        +str chave_original
        +int empresa_id FK
        +json dados
        +str resultado
        +str motivo
        +datetime importado_em
    }
    BaseModel <|-- Empresa
    BaseModel <|-- Usuario
    BaseModel <|-- AuthSession
    BaseModel <|-- LoginAttempt
    BaseModel <|-- Coletor
    BaseModel <|-- Dispositivo
    BaseModel <|-- Metrica
    BaseModel <|-- Falha
    BaseModel <|-- Impacto
    BaseModel <|-- Diagnostico
    BaseModel <|-- Recomendacao
    BaseModel <|-- DiagnosticoRecomendacao
    BaseModel <|-- RegistroLegado
    Usuario "1" *-- "0..*" AuthSession : abre
    Empresa "1" *-- "0..*" Coletor : cadastra
    Diagnostico "1" *-- "0..*" DiagnosticoRecomendacao : indica
    Recomendacao "1" o-- "0..*" DiagnosticoRecomendacao : aplicada em
    Falha "1" *-- "0..1" Diagnostico : explicada por
    Coletor "0..1" o-- "0..*" Dispositivo : mede
    Empresa "1" *-- "0..*" Dispositivo : monitora
    Dispositivo "1" *-- "0..*" Falha : apresenta
    Falha "1" *-- "1" Impacto : tem
    Coletor "0..1" --> "0..*" Metrica : enviou
    Dispositivo "1" *-- "0..*" Metrica : gera
    Empresa "0..1" --> "0..*" RegistroLegado : origem
    Empresa "1" *-- "0..*" Usuario : possui
```

## Relacionamentos

Cardinalidade lida das chaves estrangeiras: `1` quando a FK é obrigatória, `0..1` quando aceita vazio, e `1 : 1` quando
a FK é única (`Impacto` e `Diagnostico` de uma `Falha`).

| Relação | Chave estrangeira | Tipo | Cardinalidade | Por quê |
|---|---|---|---|---|
| Usuario → AuthSession | `auth_sessions.usuario_id` | Composição | 1 : 0..* | sessão é apagada junto com o usuário (ON DELETE CASCADE) |
| Empresa → Coletor | `coletores.empresa_id` | Composição | 1 : 0..* | coletor pertence a uma única empresa |
| Diagnostico → DiagnosticoRecomendacao | `diagnostico_recomendacoes.diagnostico_id` | Composição | 1 : 0..* | vínculo apagado junto com o diagnóstico (CASCADE) |
| Recomendacao → DiagnosticoRecomendacao | `diagnostico_recomendacoes.recomendacao_id` | Agregação | 1 : 0..* | o catálogo de recomendações existe sem diagnósticos |
| Falha → Diagnostico | `diagnosticos.falha_id` | Composição | 1 : 0..1 | análise por regras da própria falha |
| Coletor → Dispositivo | `dispositivos.coletor_id` | Agregação | 0..1 : 0..* | o dispositivo existe sem coletor (worker local) e pode trocar de coletor |
| Empresa → Dispositivo | `dispositivos.empresa_id` | Composição | 1 : 0..* | inventário de uma única empresa |
| Dispositivo → Falha | `falhas.dispositivo_id` | Composição | 1 : 0..* | ocorrência é sempre de um dispositivo |
| Falha → Impacto | `impactos.falha_id` | Composição | 1 : 1 | criado junto com a falha (usuários afetados e custos diretos) |
| Coletor → Metrica | `metricas.coletor_id` | Associação | 0..1 : 0..* | apenas registra a origem da amostra (vazio = worker local) |
| Dispositivo → Metrica | `metricas.dispositivo_id` | Composição | 1 : 0..* | amostra só faz sentido para o dispositivo medido |
| Empresa → RegistroLegado | `registros_legados.empresa_id` | Associação | 0..1 : 0..* | registro importado do protótipo; a empresa pode não ter sido reconhecida |
| Empresa → Usuario | `usuarios.empresa_id` | Composição | 1 : 0..* | conta de usuário só existe dentro de uma empresa |

**Legenda:** composição (losango cheio, `*--`) = a parte não existe sem o todo; agregação (losango vazio, `o--`) = a parte
existe sozinha e só é agrupada; associação (`-->`) = apenas uma referência. `Diagnostico` × `Recomendacao` é
muitos-para-muitos por meio da classe associativa `DiagnosticoRecomendacao`. `LoginAttempt` não tem relacionamento:
guarda só o hash de IP + e-mail para limitar tentativas de login.
