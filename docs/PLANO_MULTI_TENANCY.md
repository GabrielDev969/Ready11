# Plano de Implementação — Arquitetura Multi-Tenant (Ready11)

Documento de planejamento da arquitetura SaaS multi-tenant do Ready11, baseada em
**isolamento por schema** no PostgreSQL (`django-tenants`), com identidade global de
usuários, sistema de convites e controle de acesso por workspace (RBAC).

> **Stack alvo:** Python 3.12 · Django 6.0 · PostgreSQL 17 · `django-tenants`
>
> **Status:** Planejamento — nenhuma fase iniciada.

---

## Sumário

- [Visão geral da arquitetura](#visão-geral-da-arquitetura)
- [Fase 1 — Fundação Arquitetural (Multi-Tenancy e Isolamento)](#fase-1--fundação-arquitetural-multi-tenancy-e-isolamento)
- [Fase 2 — Identidade Global e Roteamento Inteligente](#fase-2--identidade-global-e-roteamento-inteligente)
- [Fase 3 — Máquina de Convites (Invite-Only)](#fase-3--máquina-de-convites-invite-only)
- [Fase 4 — Controle de Acesso e Contexto (RBAC)](#fase-4--controle-de-acesso-e-contexto-rbac)
- [Fase 5 — Provisionamento e Interfaces](#fase-5--provisionamento-e-interfaces)
- [Dependências e ordem de execução](#dependências-e-ordem-de-execução)
- [Riscos e pontos de atenção](#riscos-e-pontos-de-atenção)

---

## Visão geral da arquitetura

O objetivo é uma plataforma SaaS onde cada cliente (**Workspace** = *Tenant*) tem seus
dados fisicamente isolados em um **schema próprio** no PostgreSQL, enquanto a identidade
do usuário e os mecanismos de controle (planos, convites, permissões) vivem em um schema
**público** compartilhado.

```
┌──────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                    │
│                                                                │
│  ┌────────────────────────┐   ┌────────────────────────────┐  │
│  │  schema: public         │   │  schema: cliente_acme       │  │
│  │  (SHARED_APPS)          │   │  (TENANT_APPS)              │  │
│  │  • CustomUser           │   │  • Clientes                 │  │
│  │  • Workspace (Tenant)   │   │  • Vendas                   │  │
│  │  • Domain               │   │  • Relatórios               │  │
│  │  • WorkspaceInvite      │   └────────────────────────────┘  │
│  │  • WorkspaceMembership  │   ┌────────────────────────────┐  │
│  │  • Plan                 │   │  schema: cliente_globex      │  │
│  └────────────────────────┘   │  (TENANT_APPS replicadas)   │  │
│                                └────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Princípios:**
- Um usuário existe **uma única vez** (no `public`) e pode pertencer a vários workspaces.
- Nenhuma query de negócio cruza schemas — o isolamento é físico, não apenas lógico.
- A entrada na plataforma é **100% por convite** (invite-only).

---

## Fase 1 — Fundação Arquitetural (Multi-Tenancy e Isolamento)

Estabelecer as fronteiras físicas do banco de dados para garantir que **não exista
nenhuma possibilidade de vazamento de informações entre clientes**.

### Objetivos
- [ ] Adicionar `django-tenants` às dependências e configurar o backend de banco
      (`django_tenants.postgresql_backend`) e o `DATABASE_ROUTERS`.
- [ ] Configurar o middleware de roteamento de schema (`TenantMainMiddleware` ou
      variante por header) no topo da pilha de middlewares.
- [ ] Separar os domínios de aplicação:
  - **`SHARED_APPS`** (schema `public`): autenticação global, planos, convites e a
    tabela principal de `Workspace`. Inclui `django_tenants`, apps de auth e os apps
    de controle da plataforma.
  - **`TENANT_APPS`** (replicados por schema): aplicações de negócio (clientes,
    vendas, relatórios, etc.).
  - `INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]`.
- [ ] Modelar o **Tenant** e o **Domain**:
  - `Workspace` herda de `TenantMixin` (atua como o Tenant; guarda `schema_name`,
    nome da empresa, status, plano, datas).
  - `Domain` herda de `DomainMixin` (identificação via **subdomínio** e/ou
    **cabeçalho HTTP** nas requisições da API).
- [ ] Definir a estratégia de identificação do tenant na API:
  - Subdomínio (`acme.ready11.app`) **e/ou** header customizado (ex.: `X-Workspace-ID`).

### Entregáveis
- App `tenants` com os modelos `Workspace` e `Domain`.
- `settings.py` com `SHARED_APPS`, `TENANT_APPS`, router e middleware configurados.
- Migrações iniciais aplicadas com `migrate_schemas --shared`.

### Critérios de aceite
- É possível criar manualmente um tenant + domínio e o schema correspondente é criado
  fisicamente no PostgreSQL.
- Requisições a domínios distintos resolvem para schemas distintos.

---

## Fase 2 — Identidade Global e Roteamento Inteligente

O cadastro do usuário deve ser fluido e universal, existindo **acima dos schemas** para
permitir a transição entre contas sem atrito.

### Objetivos
- [ ] **Usuário Global (`CustomUser`)**: reside **apenas** no schema `public`
      (faz parte dos `SHARED_APPS`). E-mail **único em toda a plataforma**; login por
      e-mail (`USERNAME_FIELD = 'email'`).
- [ ] **Validador de senha estrito** (validator customizado registrado em
      `AUTH_PASSWORD_VALIDATORS`) que bloqueia o cadastro se a senha não tiver:
  - Mínimo de **8 caracteres**;
  - Pelo menos **1 número**;
  - Pelo menos **1 letra maiúscula** e **1 minúscula**;
  - Pelo menos **1 caractere especial** (símbolo).
- [ ] **Verificação de E-mail (Double Opt-in)**:
  - Geração de **token criptografado** (assinado/expirável).
  - Envio de **e-mail transacional** de confirmação.
  - A conta só é liberada para uso **após o clique** no link.
- [ ] **Motor de Roteamento — Workspace Padrão**:
  - Campo `default_workspace` (`ForeignKey` nula) no perfil do usuário.
  - **Lógica de Fallback de Login**: ao logar, o sistema verifica o `default_workspace`.
    Se ele não existir ou tiver sido desativado (ex.: o dono deletou a empresa), o
    sistema procura o **próximo workspace ativo** na tabela de permissões
    (`WorkspaceMembership`). Se não encontrar nenhum, redireciona para um estado de
    "sem workspace" (tela de espera/convite pendente), sem quebrar a sessão.

### Entregáveis
- App `accounts` com `CustomUser` + manager customizado.
- Validador de senha em `accounts/validators.py`.
- Fluxo de confirmação de e-mail (geração de token, view de confirmação, template de
  e-mail transacional).
- Serviço de resolução de login com fallback de workspace.

### Critérios de aceite
- Cadastro com senha fraca é rejeitado com mensagem clara por regra violada.
- Conta não confirmada não consegue autenticar.
- Login resolve corretamente o workspace ativo mesmo quando o `default_workspace` foi
  desativado.

---

## Fase 3 — Máquina de Convites (Invite-Only)

Garantir que a entrada no sistema seja **100% controlada**, evitando contas ociosas e
mantendo a base otimizada.

### Objetivos
- [ ] **Tabela `WorkspaceInvite`** (schema `public`): armazena `email`, `token`,
      `data de expiração`, `workspace destino` (FK) e `role` (permissão).
- [ ] **Fluxo de Convite Gênesis (Super Admin)**: interface exclusiva para disparar
      convites para futuros **Donos** de novos sistemas.
- [ ] **Fluxo de Convite Interno (Tenant Owner)**: endpoint para que o dono de um
      workspace convide a própria equipe (respeitando limites do plano).
- [ ] **Resolução Contínua** ao clicar no link do convite:
  - **Usuário novo** → tela de criar **senha e nome** (passa pela Fase 2).
  - **Usuário existente** → o sistema reconhece a sessão ativa (ou pede login) e o
    adiciona **silenciosamente** ao novo workspace, mantendo a experiência sem fricção.
- [ ] Tratamento de estados do convite: `pendente`, `aceito`, `expirado`, `revogado`.

### Entregáveis
- Modelo `WorkspaceInvite` + serviço de geração/validação de token.
- Endpoints de criação de convite (Gênesis e Interno) com checagem de permissão.
- View de aceite do convite com bifurcação usuário novo/existente.
- E-mail transacional de convite.

### Critérios de aceite
- Convite expirado ou revogado não pode ser aceito.
- Aceite de usuário existente não recria conta nem pede nova senha.
- Apenas Super Admin dispara convites Gênesis; apenas Owner/Admin disparam convites
  internos.

---

## Fase 4 — Controle de Acesso e Contexto (RBAC)

Blindagem de **quem pode ver ou editar o quê**, dependendo do workspace em que a pessoa
se encontra naquele momento.

### Objetivos
- [ ] **Tabela de Interseção `WorkspaceMembership`**: liga `User` ↔ `Workspace`,
      guardando a **role** e o **status** da relação (`ativo`, `suspenso`, `removido`).
- [ ] **Gestão de Roles**: definir os papéis (ex.: `Owner`, `Admin`, `Editor`,
      `Viewer`). Uma pessoa pode ser `Owner` no Workspace A e `Viewer` no Workspace B.
- [ ] **Middleware de Contexto HTTP**: interceptador que captura o **ID do workspace**
      acessado pelo frontend (via **Header** ou **URL**), cruza com `WorkspaceMembership`
      e **autoriza ou bloqueia** a requisição em tempo real. Injeta o contexto
      (`request.workspace`, `request.role`) para uso nas views.
- [ ] **Definição do Workspace Inicial**: o backend automatiza a regra — o **primeiro**
      workspace ao qual a pessoa é adicionada (criando um ou aceitando convite)
      preenche automaticamente o `default_workspace`.

### Entregáveis
- Modelo `WorkspaceMembership` (unique em `user + workspace`).
- Enum/choices de roles + camada de checagem de permissão por ação.
- `WorkspaceContextMiddleware`.
- Hook que preenche `default_workspace` na primeira associação.

### Critérios de aceite
- Usuário sem membership ativo no workspace recebe `403` no middleware.
- A mesma conta opera com roles diferentes em workspaces diferentes.
- O `default_workspace` é preenchido automaticamente na primeira associação.

---

## Fase 5 — Provisionamento e Interfaces

Etapa final do onboarding e transição para a operação real.

### Objetivos
- [ ] **Criação Física sob Demanda**: quando o **Dono** finaliza o cadastro e informa o
      **"Nome da Empresa"**, o backend orquestra:
  1. Criação do registro `Workspace` (Tenant) e do `Domain`;
  2. Criação do **schema** no PostgreSQL;
  3. Aplicação do **`migrate` isolado** (`migrate_schemas --schema=<novo>`);
  4. Seed inicial do tenant (role `Owner` para o criador, dados padrão);
  5. Definição do `default_workspace` se for o primeiro do usuário.
  - Executar de forma **transacional/idempotente** (idealmente assíncrono, via task)
    para não bloquear a requisição e permitir rollback em caso de falha.
- [ ] **Troca de Contexto no Front-end**: endpoints para o painel de configurações —
      uma interface minimalista onde o usuário **lista seus acessos** e **altera o
      `default_workspace` com um clique**, sem recarregar a página.

### Entregáveis
- Serviço `provision_workspace()` (criação de schema + migrate + seed) — idealmente
  disparado por task em background.
- Endpoints: `POST /workspaces` (criar), `GET /me/workspaces` (listar acessos),
  `PATCH /me/default-workspace` (trocar padrão).
- Tela de configurações de contexto (front-end).

### Critérios de aceite
- Criar empresa provisiona um schema funcional com migrações aplicadas.
- Falha no provisionamento não deixa schema/registro órfão (rollback).
- Troca de workspace padrão reflete no próximo login e na sessão atual.

---

## Dependências e ordem de execução

As fases são majoritariamente **sequenciais**, pois cada uma estabelece a fundação da
seguinte:

```
Fase 1 (Schemas/Tenant)
   └─> Fase 2 (Usuário global + login)
          └─> Fase 3 (Convites)  ──┐
          └─> Fase 4 (RBAC)       ──┼─> Fase 5 (Provisionamento + UI)
```

- **Fase 1 é pré-requisito absoluto** — sem o isolamento de schemas, nada das demais faz
  sentido.
- **Fases 3 e 4 podem avançar em paralelo** após a Fase 2, mas a Fase 4
  (`WorkspaceMembership`) é referenciada pela lógica de fallback da Fase 2 e pelo aceite
  da Fase 3 — alinhar o modelo de membership cedo.
- **Fase 5 fecha o ciclo** e depende de 1–4 prontas.

---

## Riscos e pontos de atenção

| Tema | Atenção |
|------|---------|
| Modelo de usuário | `CustomUser` precisa ser definido **antes da primeira migração** (`AUTH_USER_MODEL`). Decidir cedo. |
| `django-tenants` + Django 6 | Validar compatibilidade da versão do `django-tenants` com Django 6.0 antes de fixar no `requirements.txt`. |
| Migrações | `migrate` comum não basta — usar `migrate_schemas` (shared vs tenant). Documentar no fluxo de deploy/entrypoint. |
| Provisionamento | Criação de schema é operação pesada e não-transacional com o request — preferir execução assíncrona + idempotência. |
| Identificação do tenant | Definir cedo se será por subdomínio, header ou ambos; impacta CORS, cookies de sessão e roteamento. |
| E-mail transacional | Double opt-in e convites exigem provedor de e-mail configurado (SMTP/serviço). Definir nas variáveis de ambiente. |
| Segurança de tokens | Tokens de convite e confirmação devem ser assinados, expiráveis e de uso único. |
| `default_workspace` órfão | Garantir que desativar/deletar workspace dispare o recálculo do fallback para os usuários afetados. |

---

> Este plano é um documento vivo. Conforme cada fase é implementada, marcar os checkboxes
> e registrar decisões de arquitetura relevantes.
