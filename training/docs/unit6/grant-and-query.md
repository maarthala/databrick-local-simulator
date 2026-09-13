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

## Do it — grant analyst read-only on `demo.sales`

### In the Polaris Console
1. **Catalogs → `<your catalog>` → Catalog Roles → Create** → `sales_reader`
2. On `sales_reader` → **Grant Privilege** (one per privilege):
    - Table `demo.sales` → **`TABLE_READ_DATA`**
    - Table `demo.sales` → **`TABLE_LIST`**
    - Namespace `demo` → **`TABLE_LIST`**   *(so it shows in `SHOW TABLES`)*
    - Catalog → **`NAMESPACE_LIST`**   *(so the `demo` namespace is discoverable)*
3. On `sales_reader` → **manage principal roles → Grant to Principal Role → `analyst_role`**

### Or via the API
```bash
B=http://localhost:8185; M=$B/api/management/v1
RT=$(curl -s "$B/api/catalog/v1/oauth/tokens" --user root:s3cr3t -H 'Polaris-Realm: POLARIS' \
     -d grant_type=client_credentials -d scope=PRINCIPAL_ROLE:ALL \
     | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
H=(-H "Authorization: Bearer $RT" -H "Content-Type: application/json" -H "Polaris-Realm: POLARIS")

CAT=learn   # your catalog
curl -s "${H[@]}" -X POST "$M/catalogs/$CAT/catalog-roles" -d '{"catalogRole":{"name":"sales_reader"}}'
G="$M/catalogs/$CAT/catalog-roles/sales_reader/grants"
curl -s "${H[@]}" -X PUT "$G" -d '{"grant":{"type":"table","namespace":["demo"],"tableName":"sales","privilege":"TABLE_READ_DATA"}}'
curl -s "${H[@]}" -X PUT "$G" -d '{"grant":{"type":"table","namespace":["demo"],"tableName":"sales","privilege":"TABLE_LIST"}}'
curl -s "${H[@]}" -X PUT "$G" -d '{"grant":{"type":"namespace","namespace":["demo"],"privilege":"TABLE_LIST"}}'
curl -s "${H[@]}" -X PUT "$G" -d '{"grant":{"type":"catalog","privilege":"NAMESPACE_LIST"}}'
curl -s "${H[@]}" -X PUT "$M/principal-roles/analyst_role/catalog-roles/$CAT" -d '{"catalogRole":{"name":"sales_reader"}}'
```

## Verify — read works, write blocked

Get a token **as analyst** and exercise the table:

```bash
C=http://localhost:8185/api/catalog/v1
AT=$(curl -s "$C/oauth/tokens" --user analyst:analyst -H 'Polaris-Realm: POLARIS' \
     -d grant_type=client_credentials -d scope=PRINCIPAL_ROLE:ALL \
     | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
A=(-H "Authorization: Bearer $AT" -H 'Polaris-Realm: POLARIS')

curl -s -o /dev/null -w "list tables : %{http_code}\n" "${A[@]}" "$C/learn/namespaces/demo/tables"      # 200 (can browse)
curl -s -o /dev/null -w "read table  : %{http_code}\n" "${A[@]}" "$C/learn/namespaces/demo/tables/sales" # 200 (can read)
curl -s -o /dev/null -w "drop table  : %{http_code}\n" -X DELETE "${A[@]}" "$C/learn/namespaces/demo/tables/sales" # 403 (read-only)
```

Expected: browse **200**, read **200**, write/drop **403**.

## Query as the user

Reading through Polaris vends **short-lived, scoped MinIO credentials** — so the query
only works for tables the user is granted. To query *as analyst* from an engine, point
it at the catalog with **analyst's** client id/secret:

```python
# Spark: a catalog wired with the analyst persona's credentials
r = (spark.newSession() if False else spark)  # illustrative
spark.conf  # in practice, launch Spark/Trino with:
#   catalog.<name>.credential = analyst:analyst
# then:  SELECT * FROM <name>.demo.sales   -> works (granted); other tables -> denied
```

In this stack the pre-wired notebook `spark` connects as **root** (full access), so it's
for building/teaching; to *demonstrate* per-user enforcement, use the persona's
credentials (client id/secret) in the engine config or the Console's **Sign in** — the
persona then sees exactly what it's granted.

## Revoke
Remove a grant, unbind the role, or delete the catalog-role — access disappears
immediately (grants are checked per request).

## 🎯 This runs unchanged on Azure, Databricks, Snowflake & Fabric
This is `GRANT SELECT ON <table> TO <role>` — Databricks Unity Catalog and Snowflake use
the exact same *grant-to-a-role, read-vs-usage* model; only the syntax differs.

## You can now…
- Grant a user **read-only** access to a specific table (through a role)
- Explain why **query** (`TABLE_READ_DATA`) and **see** (`TABLE_LIST`/`NAMESPACE_LIST`) are separate
- Verify enforcement (read ✅, write ⛔) as the persona
- Query a table as a specific user via their credentials, and **revoke** access
