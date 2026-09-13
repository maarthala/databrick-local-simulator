# Cheapest-possible Databricks for learning: a Premium workspace (free until compute
# runs) + one smallest SQL warehouse that auto-stops when idle. Costs accrue ONLY
# while the warehouse is running; stopped = $0.

# Shared resource group, created by the base-setup stack.
data "azurerm_resource_group" "dbx" {
  name = var.resource_group_name
}

# Premium tier — required for SQL warehouses / serverless / Unity Catalog. No standing
# charge; billing is per-DBU only when compute runs.
resource "azurerm_databricks_workspace" "this" {
  name                = "${var.prefix}-dbw"
  resource_group_name = data.azurerm_resource_group.dbx.name
  location            = data.azurerm_resource_group.dbx.location
  sku                 = "premium"
  tags                = var.tags
}

# The smallest SQL warehouse. auto_stop_mins shuts it down when idle -> no cost.
# min/max clusters = 1 (no scaling). Serverless by default (fast start, no VM bill).
resource "databricks_sql_endpoint" "small" {
  name                      = "${var.prefix}-sqlwh"
  cluster_size              = var.warehouse_size
  auto_stop_mins            = var.auto_stop_mins
  min_num_clusters          = 1
  max_num_clusters          = 1
  enable_serverless_compute = var.serverless
  warehouse_type            = "PRO"

  tags {
    custom_tags {
      key   = "project"
      value = "adf-training"
    }
  }
}
