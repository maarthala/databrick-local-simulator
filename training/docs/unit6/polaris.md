# 6.9 Polaris: governed Iceberg for *every* engine

## Concept
Unity Catalog (6.1–6.8) taught the governance model, and you saw its OSS limits —
**Spark** governed, **Trino** not; per-user *reads* but not *writes*. **Apache
Polaris** is the other major open catalog (Snowflake's, now Apache), and it's
**Iceberg-native** — so on this stack it closes those gaps:

| | Unity Catalog (OSS here) | **Apache Polaris** |
|---|---|---|
| Governs | Spark (Delta) | **Spark *and* Trino** (Iceberg REST) |
| Per-user reads | ✅ | ✅ |
| Per-user **writes** | ❌ (pipeline only) | ✅ |
| SSO (Keycloak) | ✅ | ✅ |
| Web UI | ✅ | ✅ (Console) |

Same **concepts** as UC — catalog → namespace → table, principals, roles, grants —
so learning one teaches the other. Polaris just happens to fit an **Iceberg**
lakehouse and both engines cleanly. It maps to **Snowflake's Open Catalog** and,
conceptually, to Databricks Unity Catalog.

## How it fits the stack
```
persona (Keycloak SSO: analyst / engineer / lead)
   │  token: principal_name + principal_roles
   ▼
 Trino  &  Spark  ──(Iceberg REST)──►  Apache Polaris
   │                                      │  validates token, maps → principal + role,
   │                                      │  checks grants, vends MinIO credentials
   ▼                                      ▼
 governed reads/writes  ◄───────────  MinIO (Iceberg tables under demo-bucket/polaris/)
```
- **Catalog** `polaris_lake` on MinIO · namespaces `bronze` / `silver` / `gold`
- **Console UI**: <http://localhost:8189> (local) or `http://polaris-console.de.lan` (k8s) — Keycloak SSO login

## Lab

### 1 · Sign in to the Console with your persona (SSO)
Open the Console — **<http://localhost:8189>** (local) or **`http://polaris-console.de.lan`**
(k8s) → **Sign in with OIDC** → log in as
**`analyst` / `analyst`** (or `engineer` / `lead`). You're now browsing the
catalog *as that persona* — Keycloak authenticated you, Polaris mapped your token
to a principal and applied your grants.

### 2 · See the medallion policy enforce itself
The three personas hit the **same catalog** and get **different access** — enforced
by Polaris on your Keycloak identity, on **both** Trino and Spark:

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
SSO ties it together: the Keycloak token's **`principal_roles`** claim (from your
realm role) activates the matching Polaris principal-role, and its grants decide
what you can touch.

## What works vs. Unity Catalog here
!!! success "Polaris closes the OSS gaps"
    - **Trino *and* Spark** both governed via the standard **Iceberg REST** protocol
    - **Per-user writes** (engineer writes `silver` as themselves)
    - **Keycloak SSO** end-to-end, including the **Console UI**
    - MinIO works with **static credentials** (no STS needed)

!!! note "Runs durably on both stacks (operator note)"
    This is a real, persistent deployment, not a throwaway demo:

    - **Postgres persistence** (`polarisdb`) — the catalog, principals, and grants
      **survive restarts** (no in-memory reset).
    - **Keycloak clients** (`polaris`, `polaris-ui`) and the persona **realm roles**
      are declared in the realm JSON, so they're re-created on every Keycloak start.
    - **RBAC is seeded** by `common/polaris/seed-polaris.sh` (catalog, namespaces,
      principals, principal-/catalog-roles, graded grants) — idempotent, run once.

    Same on **Docker Compose** and **Kubernetes** (`de-stack` Helm chart); on k8s the
    Console is at `polaris-console.de.lan` and the API at `polaris.de.lan`.

## Two catalogs, one model — how to teach it
- **Unity Catalog** = the **Databricks**-world catalog (Delta + Spark). Learn the
  governance *model* here; it's what Databricks jobs use.
- **Polaris** = the **open, engine-neutral** catalog (Iceberg + Trino & Spark).
  Learn the *working, both-engine* governance here; it maps to Snowflake Open Catalog.
- The **principles are identical** — catalog/namespace/table, principals, roles,
  grants, credential vending, SSO. Pick the catalog; the governance skills transfer.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Iceberg REST catalog** | the open protocol Trino & Spark both speak → one governed catalog, every engine |
| **principal / principal-role / catalog-role** | *who* / *what roles they hold* / *the grants bundle* |
| **credential vending** | Polaris hands the engine short-lived, scoped MinIO creds after checking grants |
| **principal_roles claim** | the Keycloak token claim that activates your Polaris roles |

## You can now…
- Explain why **Polaris governs both engines** where UC-on-OSS governs only Spark
- Log into the **Console via Keycloak SSO** and see per-persona access
- Describe the RBAC chain (principal → role → catalog-role → grant) and how SSO drives it
- Choose between UC and Polaris by ecosystem (**Databricks/Delta** vs **open/Iceberg**) — same skills
