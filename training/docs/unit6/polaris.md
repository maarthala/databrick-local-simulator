# 6.1 Polaris: governed Iceberg for *every* engine

## Concept
**Unity Catalog** (Databricks' catalog, open-sourced) is one way to govern a
lakehouse, but on this OSS stack it has real limits — **Spark** governed, **Trino**
not; per-user *reads* but not *writes*. **Apache Polaris** is the other major open
catalog (Snowflake's, now Apache), and it's **Iceberg-native** — so on this stack it
closes those gaps:

| | Unity Catalog (OSS here) | **Apache Polaris** |
|---|---|---|
| Governs | Spark (Delta) | **Spark *and* Trino** (Iceberg REST) |
| Per-user reads | ✅ | ✅ |
| Per-user **writes** | ❌ (pipeline only) | ✅ |
| Login | external IdP only | **built-in** (principal id/secret) + IdP-ready |
| Web UI | ✅ | ✅ (Console) |

Same **concepts** as UC — catalog → namespace → table, principals, roles, grants —
so learning one teaches the other. Polaris just happens to fit an **Iceberg**
lakehouse and both engines cleanly. It maps to **Snowflake's Open Catalog** and,
conceptually, to Databricks Unity Catalog.

## How it fits the stack
```
persona = a Polaris principal (analyst / engineer / lead)
   │  logs in with a Client ID + Secret  →  gets a token
   ▼
 Trino  &  Spark  ──(Iceberg REST)──►  Apache Polaris
   │                                      │  identifies the principal + its roles,
   │                                      │  checks grants, vends MinIO credentials
   ▼                                      ▼
 governed reads/writes  ◄───────────  MinIO (Iceberg tables under demo-bucket/polaris/)
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
themselves (the thing UC-on-OSS couldn't do); `lead` sees the raw-PII `bronze`.

### 3 · The RBAC model (same shape as UC)
```
principal (analyst)  ──has──►  principal-role (analyst_role)
                                     │ bound to
                               catalog-role (analyst_role_cr)
                                     │ granted
                               namespace `gold` : TABLE_READ_DATA
```
The principal holds a **principal-role**, which is bound to a **catalog-role**,
whose **grants** decide exactly what it can touch. Change access once on the role
and every holder updates.

## What works vs. Unity Catalog here
!!! success "Polaris closes the OSS gaps"
    - **Trino *and* Spark** both governed via the standard **Iceberg REST** protocol
    - **Per-user writes** (engineer writes `silver` as themselves)
    - **Built-in logins** — principals sign in with a client id/secret (API *and*
      Console), no separate identity server to run
    - MinIO works with **static credentials** (no STS needed)

!!! note "Runs durably on both stacks (operator note)"
    This is a real, persistent deployment, not a throwaway demo:

    - **Postgres persistence** (`polarisdb`) — the catalog, principals, and grants
      **survive restarts** (no in-memory reset).
    - **RBAC is seeded** by `common/polaris/seed-polaris.sh` (catalog, namespaces,
      principals, principal-/catalog-roles, graded grants) — idempotent, run once.
      It also pins the persona logins (`analyst`/`analyst`, etc.).

    Same on **Docker Compose** and **Kubernetes** (`de-stack` Helm chart); on k8s the
    Console is at `polaris-console.de.lan` and the API at `polaris.de.lan`.

!!! tip "Where an IdP (SSO) would fit"
    Here, people log in with a principal's client id/secret — simplest for training.
    In production you'd front *human* logins with an identity provider (Keycloak,
    Okta, Entra): Polaris trusts the IdP's token and maps a claim → principal-role,
    so users get password/SSO + MFA while services keep using client secrets. The
    governance model below is identical either way.

## Two catalogs, one model — how to teach it
- **Unity Catalog** = the **Databricks**-world catalog (Delta + Spark). Learn the
  governance *model* here; it's what Databricks jobs use.
- **Polaris** = the **open, engine-neutral** catalog (Iceberg + Trino & Spark).
  Learn the *working, both-engine* governance here; it maps to Snowflake Open Catalog.
- The **principles are identical** — catalog/namespace/table, principals, roles,
  grants, credential vending. Pick the catalog; the governance skills transfer.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Iceberg REST catalog** | the open protocol Trino & Spark both speak → one governed catalog, every engine |
| **principal / principal-role / catalog-role** | *who* / *what roles they hold* / *the grants bundle* |
| **credential vending** | Polaris hands the engine short-lived, scoped MinIO creds after checking grants |
| **client id / secret** | how a principal (user or app) logs in — no external identity server needed |

## You can now…
- Explain why **Polaris governs both engines** where UC-on-OSS governs only Spark
- Log into the **Console as a persona** (client id/secret) and see per-persona access
- Describe the RBAC chain (principal → role → catalog-role → grant) that drives access
- Choose between UC and Polaris by ecosystem (**Databricks/Delta** vs **open/Iceberg**) — same skills
