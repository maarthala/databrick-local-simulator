output "resource_group_name" {
  description = "Resource group holding the dev SQL environment."
  value       = azurerm_resource_group.adf.name
}

output "sql_server_name" {
  description = "Logical SQL Server name."
  value       = azurerm_mssql_server.adf.name
}

output "sql_server_fqdn" {
  description = "Fully-qualified server name (use this as the ADF linked-service host)."
  value       = azurerm_mssql_server.adf.fully_qualified_domain_name
}

output "sql_database_name" {
  description = "Database name."
  value       = azurerm_mssql_database.adf.name
}

output "sql_admin_login" {
  description = "Administrator login."
  value       = var.sql_admin_login
}

output "sqlcmd_example" {
  description = "Example sqlcmd connection (password omitted — pass it with -P)."
  value       = "sqlcmd -S ${azurerm_mssql_server.adf.fully_qualified_domain_name} -d ${azurerm_mssql_database.adf.name} -U ${var.sql_admin_login} -P '<password>' -N -C"
}

output "ado_net_connection_string" {
  description = "ADO.NET connection string (sensitive — contains the password). Reveal with: terraform output -raw ado_net_connection_string"
  sensitive   = true
  value       = "Server=tcp:${azurerm_mssql_server.adf.fully_qualified_domain_name},1433;Initial Catalog=${azurerm_mssql_database.adf.name};Persist Security Info=False;User ID=${var.sql_admin_login};Password=${var.sql_admin_password};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
}
