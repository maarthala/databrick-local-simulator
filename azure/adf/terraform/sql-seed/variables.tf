# Standalone seed stack — optional. Runs seed.sql against an EXISTING SQL database
# via sqlcmd. Kept separate from the sql/ stack so provisioning never depends on
# sqlcmd (Windows users often hit sqlcmd issues). If you don't have sqlcmd, run
# seed.sql from Azure Data Studio / SSMS instead — see README.

variable "prefix" {
  description = "Same prefix used by the sql/ stack — server is <prefix>-sql."
  type        = string
  default     = "epireum"
}

variable "sql_server_fqdn" {
  description = "Server FQDN. Leave empty to derive as <prefix>.database.windows.net's server, i.e. <prefix>-sql.database.windows.net."
  type        = string
  default     = ""
}

variable "sql_database_name" {
  description = "Database to seed."
  type        = string
  default     = "shopflow"
}

variable "sql_admin_login" {
  description = "SQL admin login."
  type        = string
  default     = "sqladmin"
}

variable "sql_admin_password" {
  description = "SQL admin password (matches the sql/ stack). Override via tfvars or TF_VAR_sql_admin_password."
  type        = string
  sensitive   = true
  default     = "qwert@123456"
}
