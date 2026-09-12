# SQL seed (optional, standalone)

Runs `seed.sql` (ShopFlow tables + sample rows) against the **existing** `<prefix>-sql`
database. Kept **separate** from the `sql/` stack so provisioning never depends on
`sqlcmd` — deploy `sql/` first, then seed with whatever method suits you.

## Option A — Terraform (needs `sqlcmd`)

```bash
cd azure/adf/terraform/sql-seed
export TF_VAR_sql_admin_password='qwert@123456'   # if not using the default
terraform init && terraform apply
```

Requires `sqlcmd` on your machine and the SQL firewall reachable (the `sql/` stack
opens Azure services + internet by default). Re-runs automatically when `seed.sql` changes.

## Option B — no sqlcmd (recommended on Windows)

`sqlcmd` is fiddly on Windows. Just run the script in a GUI instead:

- **Azure Data Studio** (`winget install Microsoft.AzureDataStudio`) or **SSMS**
- Connect to `<prefix>-sql.database.windows.net`, database `shopflow`, SQL auth
  (`sqladmin` / your password)
- Open `seed.sql` → **Run**

`seed.sql` is idempotent (create-if-missing, insert-if-empty), so either option is safe
to re-run.
