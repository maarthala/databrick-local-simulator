# Databricks — cheapest learning setup (Terraform)

A **Premium workspace** (free until compute runs) + **one smallest SQL warehouse**
(`2X-Small`) that **auto-stops when idle**. Reuses the shared `common.tfvars`.

Creates: resource group → Databricks workspace `<prefix>-dbw` → serverless SQL
warehouse `<prefix>-sqlwh` (2X-Small, auto-stop 5 min, no scaling).

## Cost

- **Workspace**: $0 (no standing charge).
- **SQL warehouse**: billed **per second only while running**. When idle past
  `auto_stop_mins` it **stops → $0**.
- So you pay **only** for: query time + the short idle window before auto-stop.
- **Stopped/no queries = ~$0.** There is no continuous "instance" fee.

Keep it cheapest: leave `warehouse_size = "2X-Small"`, `serverless = true` (fast
start, no separate VM bill), and a low `auto_stop_mins`.

## Deploy

```bash
cd azure/adf/terraform/databricks
az login
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
terraform init
terraform apply -var-file=../common.tfvars
```

Then:

```bash
terraform output workspace_url        # open the workspace
terraform output sql_warehouse_jdbc   # connect BI tools / clients
```

## Teardown

```bash
terraform destroy -var-file=../common.tfvars
```

## Notes

- **Premium** tier is required for SQL warehouses / serverless / Unity Catalog — it's a
  per-DBU rate difference, not a fixed fee, so the workspace is still free until compute.
- **Serverless** must be enabled on the workspace's account (Databricks account console);
  if it's not available, set `serverless = false` for a classic warehouse (adds a VM
  bill while running, still $0 when stopped).
- The `databricks` provider authenticates via your `az login` (Azure CLI) — no PAT needed.
- Own resource group / state — independent of base-setup, sql, sql-seed.
