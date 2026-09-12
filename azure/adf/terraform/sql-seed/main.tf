# Creates a ShopFlow database on the existing <prefix>-sql server (from the sql/
# stack) and seeds it with seed.sql. Optional — the sql/ stack already gives you the
# AdventureWorks sample DB; use this only if you also want the ShopFlow schema.

# Look up the server created by the sql/ stack.
data "azurerm_mssql_server" "existing" {
  name                = "${var.prefix}-sql"
  resource_group_name = var.resource_group_name
}

# The ShopFlow database.
resource "azurerm_mssql_database" "shopflow" {
  name        = var.sql_database_name
  server_id   = data.azurerm_mssql_server.existing.id
  sku_name    = var.sku_name
  max_size_gb = 2
  collation   = "SQL_Latin1_General_CP1_CI_AS"
}

# Seed it via sqlcmd. Re-runs when seed.sql changes. Skip with run_seed=false and
# run seed.sql in Azure Data Studio / SSMS instead (see README).
resource "null_resource" "seed" {
  count = var.run_seed ? 1 : 0

  depends_on = [azurerm_mssql_database.shopflow]

  triggers = {
    seed_sha256 = filesha256("${path.module}/seed.sql")
    database    = azurerm_mssql_database.shopflow.id
  }

  provisioner "local-exec" {
    environment = {
      SQLCMDPASSWORD = var.sql_admin_password
    }
    command = "sqlcmd -S ${data.azurerm_mssql_server.existing.fully_qualified_domain_name} -d ${var.sql_database_name} -U ${var.sql_admin_login} -N -C -i ${path.module}/seed.sql"
  }
}
