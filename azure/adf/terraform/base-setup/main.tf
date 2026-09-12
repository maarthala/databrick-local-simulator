# Azure Data Factory — the empty factory (free until pipelines run), with a
# system-assigned managed identity and optional GitHub source control.

resource "azurerm_resource_group" "adf" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_data_factory" "adf" {
  name                = "${var.prefix}-adf"
  resource_group_name = azurerm_resource_group.adf.name
  location            = azurerm_resource_group.adf.location

  # Free, built-in identity the factory uses to authenticate to other Azure
  # resources later (grant it roles on SQL/Storage when you add them).
  identity {
    type = "SystemAssigned"
  }

  public_network_enabled = true

  # Enabled only when git_repository_name is set. Note: the actual GitHub auth is
  # done interactively the first time you open the factory in ADF Studio.
  dynamic "github_configuration" {
    for_each = var.git_repository_name != "" ? [1] : []
    content {
      account_name    = var.git_account_name
      repository_name = var.git_repository_name
      branch_name     = var.git_branch_name
      root_folder     = var.git_root_folder
    }
  }

  tags = var.tags
}

# --- ADLS Gen2 data lake (part of the base stack; free to create) ------------
resource "azurerm_storage_account" "dl" {
  name                     = "${var.prefix}dl"
  resource_group_name      = azurerm_resource_group.adf.name
  location                 = azurerm_resource_group.adf.location
  account_tier             = "Standard"
  account_replication_type = var.replication_type
  account_kind             = "StorageV2"
  is_hns_enabled           = true # hierarchical namespace = ADLS Gen2
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "fs" {
  for_each           = toset(var.filesystems)
  name               = each.value
  storage_account_id = azurerm_storage_account.dl.id
}
