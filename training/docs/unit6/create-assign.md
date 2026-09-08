# 6.4 Create & assign your own catalog

## Concept
[6.1](catalogs.md) explored an existing catalog and [6.2](rbac.md) read its grants. Now you'll do the
two governing actions yourself, **container-free**, from your host:

1. **create** a catalog + schema, and
2. **assign** them to a user.

The rule that shapes everything: **creating a catalog is an admin action.** A catalog is the top of
the namespace, so handing that out to everyone would break governance. On this stack there's a
dedicated **`admin`** login for it — a persona (`analyst`/`engineer`/`lead`) attempting a create gets
**`403`**. That's not a bug; it's the least-privilege model from 6.2 in force.

!!! info "Who is `admin`?"
    A Keycloak user (`admin` / `admin`) that maps to Unity Catalog's admin user and holds one special
    grant — **`CREATE CATALOG` on the metastore**. It is *not* the container's bootstrap token (that's
    an operator-only secret you never touch). `admin` is a normal login that happens to be allowed to
    create catalogs — exactly how a workspace admin works on Databricks.

## Lab

### 0 · Get an admin token (container-free)
Same `login.sh` handshake as 6.1, but as the `admin` user. The `uc` CLI on your host does the rest —
no `docker exec`, ever.

```bash
UC=http://localhost:8081
T=$(common/uc-cli/login.sh admin)                 # Keycloak login → UC token (admin / admin)
uc --server $UC --auth_token "$T" catalog list     # sanity check — lists catalogs
```

- **`T=$(… login.sh admin)`** mints a fresh token for the `admin` identity and stores it in `$T`.
- **`--auth_token "$T"`** presents that token on every call — your proof of who you are.

### 1 · Create a catalog
```bash
uc --server $UC --auth_token "$T" catalog create --name sales_cat --comment "Sales domain"
```
✅ Echoes `NAME = sales_cat`. This is admin-only — try it with an `analyst` token and you'll get
`403 PERMISSION_DENIED`.

### 2 · Create a schema inside it
```bash
uc --server $UC --auth_token "$T" schema create --catalog sales_cat --name orders
```
✅ `FULL_NAME = sales_cat.orders`.

### 3 · Assign it to a user — the grant chain
Access is **hierarchical**: a user needs `USE` at *every level* down to the object, then `SELECT` to
read. So granting `analyst` read access to `sales_cat.orders` is **three grants**. The principal is
always the user's **email**.

```bash
uc --server $UC --auth_token "$T" permission create --securable_type catalog --name sales_cat        --privilege "USE CATALOG" --principal analyst@dev-epireum.com
uc --server $UC --auth_token "$T" permission create --securable_type schema  --name sales_cat.orders --privilege "USE SCHEMA"  --principal analyst@dev-epireum.com
uc --server $UC --auth_token "$T" permission create --securable_type schema  --name sales_cat.orders --privilege "SELECT"      --principal analyst@dev-epireum.com
```

| Grant | Lets `analyst`… |
|---|---|
| `USE CATALOG` on `sales_cat` | see *into* the catalog (without it, the catalog is invisible) |
| `USE SCHEMA` on `sales_cat.orders` | see *into* the schema |
| `SELECT` on `sales_cat.orders` | read tables in it (cascades to every table; use `--securable_type table` for one) |

For an engineer/lead who should also build tables, add `--privilege "CREATE TABLE"` on the schema.

### 4 · Verify
```bash
# audit the grants you just wrote
uc --server $UC --auth_token "$T" permission get --securable_type schema --name sales_cat.orders
#  -> analyst@dev-epireum.com : ["USE SCHEMA","SELECT"]

# now BE the analyst — their own login, their own scoped view
TA=$(common/uc-cli/login.sh analyst)
uc --server $UC --auth_token "$TA" catalog list        # sales_cat now appears
```
✅ `sales_cat` shows up for `analyst` — and it wouldn't have before the grants. That's RBAC working.

### Do steps 1–2 in the Web UI instead (optional)
Log in to the UC UI ([http://localhost:3000](http://localhost:3000)) as **`admin`** → **Create
Catalog**, then **Create Schema**. The button only works because `admin` holds `CREATE CATALOG`; a
persona would be refused. **Step 3 (grants) has no UI here** — assigning access is always the
`uc … permission create` CLI.

## Gotchas you'll hit (and the fix)
| Symptom | Cause | Fix |
|---|---|---|
| `403 PERMISSION_DENIED` on create/grant | you're a persona, not `admin` | use `login.sh admin` |
| `500 … No key found … kid <x>` | your `$T` is **stale** — older than the server's current signing key | re-run `T=$(common/uc-cli/login.sh admin)`; if it persists, **open a fresh terminal** (clears stale shell state) |
| token kid ≠ server kid | leftover shell variables from earlier commands | fresh terminal, then re-fetch `$T` |
| `already exists` | name is taken | pick another, or `catalog delete --name …` |

!!! tip "One-liner that never goes stale"
    Fetch and use the token in a single command, so there's no `$T` to grow stale:
    ```bash
    uc --server http://localhost:8081 --auth_token "$(common/uc-cli/login.sh admin)" catalog list
    ```

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **`admin` login** | Keycloak user allowed to create catalogs (holds `CREATE CATALOG` on the metastore) |
| **`CREATE CATALOG`** | metastore-level privilege — the right to make new catalogs |
| **grant chain** | `USE CATALOG` → `USE SCHEMA` → `SELECT`, needed top-to-bottom to read |
| **principal** | *who* a grant is for — always the user's **email** |
| **securable** | *what* a grant is on — `catalog` / `schema` / `table` (or `metastore`) |

## You can now…
- Get an **admin** token container-free and create a **catalog + schema**
- **Assign** them to a user with the three-grant chain, and audit with `permission get`
- Confirm the result by logging in **as that user** and seeing their scoped view
- Recognise a stale-token `500` and clear it (re-fetch / fresh terminal)

On **Databricks/Snowflake/Fabric** this is the identical shape: an admin creates the catalog, then
`GRANT USE`/`SELECT` (or the Catalog-Explorer UI) assigns it — the platform's engine enforces it per
query, which the managed cloud adds on top of this same model.
