# 6.2 Users, roles & RBAC

## Concept
A catalog is only as trustworthy as its rules about **who can read what**. Unity Catalog uses
**role-based access control (RBAC)**: you `GRANT` a **privilege** on a **securable** to a
**principal**.

- **Principal** — the identity being granted (a user, e.g. `analyst@dev-epireum.com`).
- **Securable** — the object you protect: a `catalog`, `schema`, or `table`.
- **Privilege** — what they may do: `USE CATALOG`, `USE SCHEMA`, `SELECT`, `CREATE TABLE`.

The key idea is the **grant chain**. Access is *hierarchical*: to reach a table a user needs
permission at **every level above it**. `SELECT` on the table means nothing if they can't even
"enter" the catalog and schema.

```mermaid
flowchart LR
  A([analyst]) -->|USE CATALOG| C[shopflow]
  C -->|USE SCHEMA| G[gold]
  G -->|SELECT| T[daily_sales]
  style T fill:#d4edda
```

For ShopFlow we enforce the medallion access policy from [Unit 1](../unit1/medallion.md), mapped to
the three fixed [personas](../setup/personas.md):

| Persona | What they can do | Grants on `shopflow` |
|---|---|---|
| **analyst** | read the 🥇 Gold layer | `USE CATALOG` + Gold `USE SCHEMA` + `SELECT` |
| **engineer** | build in 🥈 Silver, read Gold | `USE CATALOG` + Silver `USE SCHEMA`/`SELECT`/`CREATE TABLE` + Gold `USE SCHEMA`/`SELECT` |
| **lead** | full access to every layer (owner) | `USE CATALOG` + `USE SCHEMA`/`SELECT`/`CREATE TABLE` on bronze **and** silver **and** gold |

🥉 **Bronze** raw data is granted to **lead** only — analyst and engineer are denied by default.

This policy is **pre-provisioned** on your stack (`make uc-seed`). Below you'll read how it's
*defined*, then inspect it yourself.

## Lab

### How the policy is defined
Grants are written with the `uc` CLI (by an admin or the object's owner). This is the exact chain
that gives the **analyst** persona read access to Gold:

```bash
uc --server $UC --auth_token "$ADMIN" permission create \
  --securable_type catalog --name shopflow \
  --privilege "USE CATALOG" --principal analyst@dev-epireum.com

uc --server $UC --auth_token "$ADMIN" permission create \
  --securable_type schema --name shopflow.gold \
  --privilege "USE SCHEMA" --principal analyst@dev-epireum.com

uc --server $UC --auth_token "$ADMIN" permission create \
  --securable_type table --name shopflow.gold.daily_sales \
  --privilege "SELECT" --principal analyst@dev-epireum.com
```

Granting `SELECT` on the **schema** instead of a single table cascades to every current and future
table in it — the cleanest way to give layer-wide read.

### Inspect the policy (container-free)
Log in as yourself and read the grants that are in force — no container shell needed:

```bash
export UC=http://localhost:8081 UC_URL=http://localhost:8081
export KC_URL=http://keycloak:8080/realms/de-stack/protocol/openid-connect/token
T=$(common/uc-cli/login.sh analyst)

# who can do what on gold?
uc --server $UC --auth_token "$T" permission get --securable_type schema --name shopflow.gold
#  -> analyst@dev-epireum.com : USE SCHEMA, SELECT

# and on silver?
uc --server $UC --auth_token "$T" permission get --securable_type schema --name shopflow.silver
#  -> engineer@dev-epireum.com : USE SCHEMA, SELECT, CREATE TABLE
#  -> lead@dev-epireum.com     : USE SCHEMA, SELECT, CREATE TABLE
```

Note **bronze** is granted only to **lead** — raw data stays locked to the data lead and admins.

!!! warning "Enforcement: model here, engine on the cloud"
    You just **defined and inspected** a real access policy. On **Databricks Unity Catalog** the
    query engines call UC before returning a row, so this policy is *enforced automatically* —
    the analyst reads Gold but is denied Silver/Bronze. On this OSS compose stack the engines (Trino/Spark) aren't
    wired to UC, so enforcement isn't live here — but the **grant model is identical** and
    transfers 1:1. Learn the policy design; the managed cloud makes it bite.

!!! note "UC OSS has no roles or groups"
    In this edition, grants are **per-user** — no `CREATE ROLE`, no groups. To give five analysts
    access you grant each individually (or script it). Databricks and Snowflake add first-class
    **roles/groups**; the privilege model is otherwise the same.

## Challenge
A new analyst, **carol**, must read **all** of Gold — including future tables — without a per-table
grant. Write the grant chain that achieves it (schema-level `SELECT`), and say why granting at the
schema (not table) level is the right choice.

??? note "Solution"
    ```bash
    # (admin/owner) — carol gets the analyst chain, SELECT at the schema level
    uc --server $UC --auth_token "$ADMIN" permission create \
      --securable_type catalog --name shopflow \
      --privilege "USE CATALOG" --principal carol@dev-epireum.com
    uc --server $UC --auth_token "$ADMIN" permission create \
      --securable_type schema --name shopflow.gold \
      --privilege "USE SCHEMA" --principal carol@dev-epireum.com
    uc --server $UC --auth_token "$ADMIN" permission create \
      --securable_type schema --name shopflow.gold \
      --privilege "SELECT" --principal carol@dev-epireum.com
    ```
    Schema-level `SELECT` **cascades** to every current and future table in `gold`, so you never
    re-grant when a new mart lands.

!!! tip "🎯 The same grant model on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** defined and inspected the `USE CATALOG → USE SCHEMA → SELECT` grant chain.

    - **Azure Databricks** — *identical*: the same `GRANT USE CATALOG / USE SCHEMA / SELECT` on
      Unity Catalog, enforced automatically; the upgrade is granting to **groups** synced from **Entra ID**.
    - **Snowflake** — RBAC via first-class **roles**: `GRANT USAGE ON DATABASE/SCHEMA` +
      `GRANT SELECT ON TABLE … TO ROLE analyst`.
    - **Microsoft Fabric** — **Workspace roles** + **Microsoft Purview** policies.
    - **Azure Data Factory** — no table RBAC of its own; governance belongs to UC / Purview.

    Same idea everywhere: **principal + securable + privilege**, in a hierarchical chain.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Principal** | The identity being granted (user / group) |
| **Securable** | The protected object (catalog / schema / table) |
| **Privilege** | The allowed action (`USE CATALOG`, `SELECT`, …) |
| **Grant chain** | You need permission at *every* level above a table |
| **Cascade** | A schema-level grant covers all its tables |
| **`permission get`** | Inspect the grants on a securable (container-free) |

## You can now…
- Define principals, securables, privileges, and trace the grant chain to a table
- Read a layer's access policy container-free with `permission get`
- Explain the analyst-on-Gold / engineer-on-Silver / locked-Bronze policy
- Say where enforcement happens (engine-side; automatic on managed Databricks UC)
