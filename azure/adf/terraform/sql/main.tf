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
