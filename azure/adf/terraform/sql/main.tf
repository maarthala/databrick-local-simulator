# Azure SQL dev environment for the ADF training: a logical SQL Server + one database
# that Azure Data Factory connects to as a source/sink. Kept intentionally small/cheap.

resource "azurerm_resource_group" "adf" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# The logical SQL Server (the host; databases live under it).
resource "azurerm_mssql_server" "adf" {
  name                          = "${var.prefix}-sql"
  resource_group_name           = azurerm_resource_group.adf.name
  location                      = azurerm_resource_group.adf.location
  version                       = "12.0"
  administrator_login           = var.sql_admin_login
  administrator_login_password  = var.sql_admin_password
  minimum_tls_version           = "1.2"
  public_network_access_enabled = true
  tags                          = var.tags
}

# The database ADF will use.
resource "azurerm_mssql_database" "adf" {
  name        = var.sql_database_name
  server_id   = azurerm_mssql_server.adf.id
  sku_name    = var.sku_name
  max_size_gb = var.max_size_gb
  collation   = "SQL_Latin1_General_CP1_CI_AS"
  tags        = var.tags
}

# Allow Azure services (incl. Azure Data Factory's default Azure integration runtime)
# to reach the server. The 0.0.0.0 "rule" is Azure's special allow-Azure-services flag.
resource "azurerm_mssql_firewall_rule" "allow_azure" {
  count            = var.allow_azure_services ? 1 : 0
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.adf.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Open the server to all public IPs (dev/learning). Insecure — login still required.
resource "azurerm_mssql_firewall_rule" "internet" {
  count            = var.allow_all_internet ? 1 : 0
  name             = "AllowAllInternet"
  server_id        = azurerm_mssql_server.adf.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}

# Optionally allow your workstation to connect (SSMS / Azure Data Studio / sqlcmd).
resource "azurerm_mssql_firewall_rule" "client" {
  count            = var.client_ip != "" ? 1 : 0
  name             = "DevWorkstation"
  server_id        = azurerm_mssql_server.adf.id
  start_ip_address = var.client_ip
  end_ip_address   = var.client_ip
}

# Seed the database after it's created — runs seed.sql via sqlcmd from the machine
# running Terraform. Requires: sqlcmd installed (brew install sqlcmd) + firewall open
# to this machine (allow_all_internet or client_ip). Password passed via SQLCMDPASSWORD
# env so it isn't echoed in logs. Re-runs only when seed.sql changes.
resource "null_resource" "seed" {
  count = var.run_seed ? 1 : 0

  depends_on = [
    azurerm_mssql_database.adf,
    azurerm_mssql_firewall_rule.allow_azure,
    azurerm_mssql_firewall_rule.internet,
  ]

  triggers = {
    database    = azurerm_mssql_database.adf.id
    seed_sha256 = filesha256("${path.module}/seed.sql")
  }

  provisioner "local-exec" {
    environment = {
      SQLCMDPASSWORD = var.sql_admin_password
    }
    command = "sqlcmd -S ${azurerm_mssql_server.adf.fully_qualified_domain_name} -d ${var.sql_database_name} -U ${var.sql_admin_login} -N -C -i ${path.module}/seed.sql"
  }
}
