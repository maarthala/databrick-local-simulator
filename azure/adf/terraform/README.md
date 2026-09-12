# Azure ADF — Terraform

Infrastructure-as-Code for the Azure Data Factory learning environment, split into
small independent **stacks** (each with its own state — deploy/destroy separately).

```
base-setup/   ADF factory (+ GitHub) + ADLS Gen2 data lake   (free until pipelines run)
sql/          Azure SQL logical server + database             (billable ~US$5/mo)
sql-seed/     runs seed.sql into the SQL db (optional)        (needs sqlcmd, or use a GUI)
```

Naming is driven by a single **`prefix`** variable (default `epireum`), so resources
get static names: `epireum-adf`, `epireumdl`, `epireum-sql`.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/downloads) ≥ 1.5
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), signed in:

```bash
az login
az account set --subscription azur-learning
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
```

## One shared variables file (`common.tfvars`)

**All** stacks read from a single `common.tfvars` — there are no per-stack tfvars.

```bash
cp common.tfvars.example common.tfvars   # edit once; gitignored (has the password)
```

Pass it to every stack with `-var-file` (path relative to the stack you run from):

```bash
cd base-setup && terraform apply -var-file=../common.tfvars
cd ../sql     && terraform apply -var-file=../common.tfvars
cd ../sql-seed && terraform apply -var-file=../common.tfvars
```

Each stack uses the variables it declares; any it doesn't just print a harmless
`Value for undeclared variable` warning (add `-compact-warnings` to trim). Put only
**shared** values here (`subscription_id`, `prefix`, SQL creds, git). Values that
**differ** per stack (location, resource group, database name) are NOT in the file —
they come from each stack's own defaults in `variables.tf`.

## Deploy

```bash
cd azure/adf/terraform
cp common.tfvars.example common.tfvars     # edit values

# 1. base (ADF + data lake) — free
cd base-setup && terraform init && terraform apply -var-file=../common.tfvars

# 2. SQL server + AdventureWorks sample DB — billable
cd ../sql && terraform init && terraform apply -var-file=../common.tfvars

# 3. optional ShopFlow DB + seed (needs sqlcmd, or seed in a GUI)
cd ../sql-seed && terraform init && terraform apply -var-file=../common.tfvars
```

## Destroy

Each stack independently (SQL is the only one that costs money):

```bash
cd sql        && terraform destroy -var-file=../common.tfvars
cd ../base-setup && terraform destroy -var-file=../common.tfvars
```

## Notes

- **State is local** per stack (`terraform.tfstate`). Fine for solo dev; use a remote
  backend (Azure Storage) for a team.
- **Secrets/state are gitignored** — `*.tfvars`, `*.tfstate*`, `.terraform/`. Only
  `*.tf`, `*.tfvars.example`, READMEs, and the lock files are committed.
- `prefix` must be **globally unique** (storage + SQL server names are global). Change
  it in `common.tfvars` if `epireum` is taken.
- `sql/` creates the **AdventureWorks** sample DB (Azure-populated, no seeding);
  `sql-seed/` optionally adds a separate **ShopFlow** DB and seeds it.
