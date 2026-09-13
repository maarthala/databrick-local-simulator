output "workspace_url" {
  description = "Databricks workspace URL."
  value       = "https://${azurerm_databricks_workspace.this.workspace_url}"
}

output "workspace_id" {
  value = azurerm_databricks_workspace.this.id
}

output "sql_warehouse_id" {
  value = databricks_sql_endpoint.small.id
}

output "sql_warehouse_jdbc" {
  description = "JDBC URL for the SQL warehouse (for BI tools / clients)."
  value       = databricks_sql_endpoint.small.jdbc_url
}
