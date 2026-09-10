output "resource_group_name" {
  value = azurerm_resource_group.adf.name
}

output "data_factory_name" {
  value = azurerm_data_factory.adf.name
}

output "data_factory_id" {
  value = azurerm_data_factory.adf.id
}

# The factory's system-assigned managed identity — grant this object id roles on
# SQL/Storage so the factory can connect without stored credentials.
output "identity_principal_id" {
  description = "Object (principal) id of the factory's managed identity."
  value       = azurerm_data_factory.adf.identity[0].principal_id
}

output "adf_studio_url" {
  description = "Open the factory in ADF Studio."
  value       = "https://adf.azure.com/en/home?factory=${azurerm_data_factory.adf.id}"
}

output "storage_account_name" {
  value = azurerm_storage_account.dl.name
}

output "dfs_endpoint" {
  description = "ADLS Gen2 (dfs) endpoint — host for the ADF linked service."
  value       = azurerm_storage_account.dl.primary_dfs_endpoint
}

output "filesystems" {
  value = keys(azurerm_storage_data_lake_gen2_filesystem.fs)
}
