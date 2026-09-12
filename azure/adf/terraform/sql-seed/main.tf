# Runs seed.sql against the existing <prefix>-sql database via sqlcmd. Re-runs when
# seed.sql changes. Requires sqlcmd on this machine + firewall reachable. No cloud
# resources are created here — this only executes the script.

locals {
  server_fqdn = var.sql_server_fqdn != "" ? var.sql_server_fqdn : "${var.prefix}-sql.database.windows.net"
}

resource "null_resource" "seed" {
  triggers = {
    seed_sha256 = filesha256("${path.module}/seed.sql")
    server      = local.server_fqdn
    database    = var.sql_database_name
  }

  provisioner "local-exec" {
    environment = {
      SQLCMDPASSWORD = var.sql_admin_password
    }
    command = "sqlcmd -S ${local.server_fqdn} -d ${var.sql_database_name} -U ${var.sql_admin_login} -N -C -i ${path.module}/seed.sql"
  }
}
