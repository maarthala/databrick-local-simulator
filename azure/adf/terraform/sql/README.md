# Azure SQL — dev environment for ADF (Terraform)

Provisions the **Azure SQL Server + database** that Azure Data Factory connects to as a
source/sink, as Infrastructure-as-Code. Small and cheap by design (Basic tier by default).

What it creates:

- a **resource group** (`rg-adf-dev`)
- an **Azure SQL logical server** (`<prefix>-sql-<random>`, TLS 1.2, SQL auth)
- an **Azure SQL database** (`shopflow`, Basic SKU)
- **firewall rules**: allow Azure services (so ADF can connect) + optionally your workstation IP

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/downloads) ≥ 1.5
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) — signed in: `az login`
- An Azure subscription with rights to create resources

## Use it

```bash
cd microsoft/adf/terraform

# 1. sign in and pick the subscription
az login
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# 2. set your variables (secrets stay out of git)
cp terraform.tfvars.example terraform.tfvars
#   edit terraform.tfvars — at minimum set sql_admin_password
#   (or, better, keep it out of files entirely:)
export TF_VAR_sql_admin_password='<a strong 12+ char password>'

# 3. provision
terraform init
terraform plan
terraform apply
```

Handy after apply:

```bash
terraform output sql_server_fqdn                 # host for the ADF linked service
terraform output -raw ado_net_connection_string  # full connection string (sensitive)
```

## Connect / verify

Set `client_ip` (your public IP — `curl -s ifconfig.me`) in `terraform.tfvars`, re-apply, then:

```bash
sqlcmd -S "$(terraform output -raw sql_server_fqdn)" -d shopflow \
  -U sqladmin -P "$TF_VAR_sql_admin_password" -N -C -Q "SELECT @@VERSION;"
```

## Wire it into Azure Data Factory

In ADF Studio → **Manage → Linked services → New → Azure SQL Database**:

- **Fully qualified domain name**: `terraform output -raw sql_server_fqdn`
- **Database name**: `shopflow`
- **Authentication**: SQL authentication — user `sqladmin`, the password you set

`allow_azure_services = true` lets ADF's default Azure integration runtime reach the
server. (For production you'd use a Managed Identity + Private Endpoint instead of the
allow-Azure-services rule + SQL auth.)

## Cost & teardown

Basic tier is ~US$5/month. **Destroy it when you're done** so it costs nothing:

```bash
terraform destroy
```

## Notes

- **State is local** (`terraform.tfstate`) — fine for a solo dev. For a team, add a
  remote backend (Azure Storage) so state is shared and locked.
- **Secrets**: `*.tfvars` and `*.tfstate*` are gitignored. The admin password lives only
  in your tfvars/env and in local state — never commit them.
- **SKU**: switch `sku_name` to `S0`/`S1` for more throughput, or `GP_S_Gen5_1` for
  serverless (auto-pauses when idle — cheaper for intermittent dev use).
