# 6.1 Polaris: governed Iceberg for *every* engine

## Concept
The lakehouse stores tables; a **catalog** governs them — who can see and touch what.
This stack uses **Apache Polaris** (Snowflake's, now Apache), an **Iceberg-native**
governed REST catalog. It gives you, on one shared lakehouse:

- **Both engines governed** — Trino *and* Spark, through the standard **Iceberg REST** protocol
- **Per-user reads *and* writes** — enforced on the identity making the request
- **Built-in logins** — principals sign in with a client id/secret (API *and* Console); no separate identity server
- **Credential vending** — Polaris hands each engine short-lived, scoped MinIO credentials after checking grants
- **A web Console** to manage catalogs, namespaces, roles, and grants

The model is the universal one — **catalog → namespace → table**, with **principals,
roles, grants** — so the skills transfer straight to the cloud catalogs
([10.1](../platforms/rosetta.md)).

## How it fits the stack
```
persona = a Polaris principal (analyst / engineer / lead)
   │  logs in with a Client ID + Secret  →  gets a token
   ▼
 Trino  &  Spark  ──(Iceberg REST)──►  Apache Polaris
   │                                      │  identifies the principal + its roles,
   │                                      │  checks grants, vends MinIO credentials
   ▼                                      ▼
 governed reads/writes  ◄───────────  MinIO (Iceberg tables under demo-bucket/warehouse/)
```
- **Catalog** `polaris_lake` on MinIO · namespaces `bronze` / `silver` / `gold`
- **Console UI**: <http://localhost:8189> (local) or `http://polaris-console.de.lan` (k8s)
- **No separate identity server** — principals authenticate to Polaris directly.

!!! info "This governs the *real* tables you already built"
    `polaris_lake` is the very same catalog your engines call **`iceberg`** — the one
    the whole pipeline writes to in Units 2–5. So the medallion tables you queried as
    `iceberg.gold.daily_sales` are exactly what these personas get graded access to.
    One governed catalog, used by everything (Trino, Spark, the Console).

## Lab

### 1 · Sign in to the Console as your persona
Open the Console — **<http://localhost:8189>** (local) or **`http://polaris-console.de.lan`**
(k8s) — and sign in with a persona's **Client ID / Client Secret**:
**`analyst` / `analyst`** (or `engineer` / `lead`; admin is `root` / `s3cr3t`).
You're now browsing the catalog *as that persona* — Polaris identifies the
principal and applies its grants.

### 2 · See the medallion policy enforce itself
The three personas hit the **same catalog** and get **different access** — enforced
by Polaris on the principal's roles, on **both** Trino and Spark:

| Persona | `gold` | `silver` | `bronze` |
|---|---|---|---|
| **analyst** (BI) | ✅ read | ⛔ | ⛔ |
| **engineer** (pipelines) | ✅ read | ✅ **read + write** | ⛔ |
| **lead** (owner) | ✅ | ✅ | ✅ |

`analyst` can't even *see* `silver`/`bronze`; `engineer` can **write** `silver` as
themselves; `lead` sees the raw-PII `bronze`.

### 3 · The RBAC model
```
principal (analyst)  ──has──►  principal-role (analyst_role)
                                     │ bound to
                               catalog-role (analyst_role_cr)
                                     │ granted
                               namespace `gold` : TABLE_READ_DATA
```
The principal holds a **principal-role**, which is bound to a **catalog-role**,
whose **grants** decide exactly what it can touch. Change access once on the role
and every holder updates. (You'll build this yourself in [6.3](create-catalog-table.md)
and [6.4](grant-and-query.md).)

## What you get here
!!! success "One governed catalog for the whole lakehouse"
    - **Trino *and* Spark** both governed via the standard **Iceberg REST** protocol
    - **Per-user reads and writes** (engineer writes `silver` as themselves)
    - **Built-in logins** — principals sign in with a client id/secret (API *and* Console)
    - MinIO works with **static credentials** (no STS needed)

!!! note "Runs durably on both stacks (operator note)"
    This is a real, persistent deployment, not a throwaway demo:

    - **Postgres persistence** (`polarisdb`) — the catalog, principals, and grants
      **survive restarts** (no in-memory reset).
    - **RBAC is seeded** by the operator (catalog, namespaces, principals,
      principal-/catalog-roles, graded grants) — idempotent, run once. It also pins the
      persona logins (`analyst`/`analyst`, etc.).

    Same on **Docker Compose** and **Kubernetes** (`de-stack` Helm chart); on k8s the
    Console is at `polaris-console.de.lan` and the API at `polaris.de.lan`.

!!! tip "Where an IdP (SSO) would fit"
    Here, people log in with a principal's client id/secret — simplest for training.
    In production you'd front *human* logins with an identity provider (Keycloak,
    Okta, Entra): Polaris trusts the IdP's token and maps a claim → principal-role,
    so users get password/SSO + MFA while services keep using client secrets. The
    governance model is identical either way.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Iceberg REST catalog** | the open protocol Trino & Spark both speak → one governed catalog, every engine |
| **principal / principal-role / catalog-role** | *who* / *what roles they hold* / *the grants bundle* |
| **credential vending** | Polaris hands the engine short-lived, scoped MinIO creds after checking grants |
| **client id / secret** | how a principal (user or app) logs in — no external identity server needed |

## You can now…
- Explain how **Polaris governs both engines** (Trino + Spark) over one Iceberg lakehouse
- Log into the **Console as a persona** (client id/secret) and see per-persona access
- Describe the RBAC chain (principal → role → catalog-role → grant) that drives access
- Map the model to the cloud catalogs (Databricks / Snowflake / Fabric) — same concepts
