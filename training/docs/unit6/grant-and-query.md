# 6.4 Grant table access to a user & query it

You have personas ([6.2](polaris-admin.md)) and tables ([6.3](create-catalog-table.md)).
Now the everyday governance task: **give a user read access to a specific table**, then
**query it as that user**.

## The one thing that trips everyone: read ≠ see

Two *different* capabilities, each its own privilege:

| Goal | Privilege | Scope |
|---|---|---|
| **Query** the table (read rows) | `TABLE_READ_DATA` | the table |
| **See / browse** it (`SHOW TABLES`, Console tree) | `TABLE_LIST` | the **namespace** |
| See the namespace exists | `NAMESPACE_LIST` | the **catalog** |
| Write / insert / drop | `TABLE_WRITE_DATA`, `TABLE_CREATE`, … | the table/namespace |

A user with only `TABLE_READ_DATA` can query the table **if they know its exact name**,
but it won't show up when they browse — that needs the two `*_LIST` privileges. For
**read-only query + discovery**, grant: `TABLE_READ_DATA` + `TABLE_LIST` (namespace) +
`NAMESPACE_LIST` (catalog). No write privileges = read-only.

## The grant chain (always through a role)

You never grant a user directly — access flows **user → principal-role → catalog-role → grant**:

```
analyst (principal) ─► analyst_role ─► sales_reader (catalog-role) ─► TABLE_READ_DATA + LIST on demo.sales
```

!!! note "Permissions are set in the Console UI"
    Polaris manages its own RBAC — you grant access in the **Polaris Console**, *not*
    with SQL. `GRANT` in Spark or Trino does **not** work against Polaris (the engines
    only read/write data; the catalog owns access control).

## Do it — grant analyst read-only on `demo.sales` (Console)

Sign in to the Console (<http://localhost:8189>) as `root` / `s3cr3t`.

**1. Create the catalog role:** Catalogs → `<your catalog>` → **Catalog Roles → Create** → name it `sales_reader`.

**2. Add these grants** — on `sales_reader` → **Grant Privilege** (one grant per row):

| Scope | Resource | Privilege | Why |
|---|---|---|---|
| Table | `demo.sales` | **`TABLE_READ_DATA`** | read the rows |
| Table | `demo.sales` | **`TABLE_LIST`** | see the table |
| Namespace | `demo` | **`TABLE_LIST`** | list tables in `demo` |
| Catalog | — | **`NAMESPACE_LIST`** | discover the `demo` namespace |

**3. Bind it to the persona:** on `sales_reader` → **manage principal roles → Grant to Principal Role → `analyst_role`**.

That's it — analyst now has read-only access, granted through the role.

## Verify (in the UI)

Sign out and **sign back in to the Console as `analyst` / `analyst`**:

- You can **see** the `demo` namespace and the `sales` table, and **open** it → ✅ read works.
- **Create / Delete** actions on it are unavailable → ⛔ it's read-only.

Log back in as `root` to keep administering.

## Query it

Reading through Polaris vends **short-lived, scoped credentials** — a user can only read
tables they're granted. Whoever queries as **analyst** (signed into the Console, or an
engine configured with analyst's client id/secret) sees exactly `demo.sales` and nothing
they weren't granted. The pre-wired notebook `spark` connects as **root** (full access),
so use it for building/teaching; to *demonstrate* per-user enforcement, sign in as the
persona.

## Revoke
In the Console, remove a grant, unbind the role, or delete the catalog-role — access
disappears immediately (grants are checked per request).

## 🎯 This runs unchanged on Azure, Databricks, Snowflake & Fabric
This is `GRANT SELECT ON <table> TO <role>` — the Databricks catalog and Snowflake use
the exact same *grant-to-a-role, read-vs-usage* model; only the syntax differs.

## You can now…
- Grant a user **read-only** access to a specific table (through a role)
- Explain why **query** (`TABLE_READ_DATA`) and **see** (`TABLE_LIST`/`NAMESPACE_LIST`) are separate
- Verify enforcement (read ✅, write ⛔) as the persona
- Query a table as a specific user via their credentials, and **revoke** access
