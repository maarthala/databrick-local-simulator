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

## Shared variables (`common.tfvars`)

The two SQL stacks (`sql/`, `sql-seed/`) share settings via one file:

```bash
cp common.tfvars.example common.tfvars   # edit values; gitignored (has the password)
```

Pass it with `-var-file` (path is relative to the stack you run from):

```bash
cd sql      && terraform apply -var-file=../common.tfvars
cd ../sql-seed && terraform apply -var-file=../common.tfvars
```

`common.tfvars` may contain **only variables declared in both** stacks — `prefix`,
`sql_admin_login`, `sql_admin_password`, `sql_database_name`. (Terraform errors on an
undefined variable.) `base-setup/` has a different variable set, so it uses its own
`terraform.tfvars`.

## Deploy

```bash
# 1. base (ADF + data lake) — free
cd base-setup
cp terraform.tfvars.example terraform.tfvars   # set prefix, git repo, etc.
terraform init && terraform apply

# 2. SQL server + database — billable
cd ../sql
terraform init && terraform apply -var-file=../common.tfvars

# 3. seed the SQL db (optional)
cd ../sql-seed
terraform init && terraform apply -var-file=../common.tfvars
#   no sqlcmd? skip this and run seed.sql in Azure Data Studio / SSMS instead
#   (see sql-seed/README.md)
```

## Destroy

Each stack independently (SQL is the only one that costs money):

```bash
cd sql      && terraform destroy -var-file=../common.tfvars
cd base-setup && terraform destroy
```

## Notes

- **State is local** per stack (`terraform.tfstate`). Fine for solo dev; use a remote
  backend (Azure Storage) for a team.
- **Secrets/state are gitignored** — `*.tfvars`, `*.tfstate*`, `.terraform/`. Only
  `*.tf`, `*.tfvars.example`, READMEs, and the lock files are committed.
- `prefix` must be **globally unique** (storage + SQL server names are global). Change
  it in `common.tfvars` / `base-setup/terraform.tfvars` if `epireum` is taken.
