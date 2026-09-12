# ShopFlow database + seed (optional)

The `sql/` stack already gives you a ready-to-use **AdventureWorks** sample database
(Azure populates it — no seeding). Use **this** stack only if you *also* want a
**ShopFlow** database with the custom schema.

It **creates** a `shopflow` database on the existing `<prefix>-sql` server and seeds it
with `seed.sql` (customers, products, orders, order_items, metadata).

## Prerequisite

Deploy the `sql/` stack first (this looks up its server by name `<prefix>-sql`).

## Option A — Terraform (needs `sqlcmd`)

```bash
cd azure/adf/terraform/sql-seed
terraform init
terraform apply -var-file=../common.tfvars
```

Creates the DB and runs the seed. Requires `sqlcmd` + firewall reachable (the `sql/`
stack opens Azure services + internet by default).

## Option B — no sqlcmd (recommended on Windows)

Create the empty DB with Terraform, seed with a GUI:

```bash
terraform apply -var-file=../common.tfvars -var run_seed=false
```

Then open `seed.sql` in **Azure Data Studio** / **SSMS** (connect to
`<prefix>-sql.database.windows.net`, database `shopflow`) and **Run**.

`seed.sql` is idempotent (create-if-missing, insert-if-empty).

## Teardown

```bash
terraform destroy -var-file=../common.tfvars
```

Removes just the ShopFlow database (leaves the server + AdventureWorks DB from `sql/`).
