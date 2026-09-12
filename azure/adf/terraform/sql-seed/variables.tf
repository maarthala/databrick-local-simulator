# Optional ShopFlow database — created ON the server from the sql/ stack, then seeded
# with seed.sql. Use only if you need the ShopFlow schema in addition to the
# AdventureWorks sample DB that sql/ provisions. Separate stack/state.

variable "subscription_id" {
  description = "Azure subscription id. Leave empty to use ARM_SUBSCRIPTION_ID from the environment."
  type        = string
  default     = ""
}

variable "prefix" {
  description = "Same prefix as the sql/ stack — the existing server is <prefix>-sql."
  type        = string
  default     = "epireum"
}

variable "resource_group_name" {
  description = "Resource group of the existing SQL server (from the sql/ stack)."
  type        = string
  default     = "rg-adf-sql"
}

variable "sql_database_name" {
  description = "Name of the ShopFlow database to create + seed."
  type        = string
  default     = "shopflow"
}

variable "sku_name" {
  description = "SKU for the ShopFlow database."
  type        = string
  default     = "Basic"
}

variable "sql_admin_login" {
  description = "SQL admin login (matches the sql/ stack)."
  type        = string
  default     = "sqladmin"
}

variable "sql_admin_password" {
  description = "SQL admin password (matches the sql/ stack). Override via tfvars or TF_VAR_sql_admin_password."
  type        = string
  sensitive   = true
  default     = "qwert@123456"
}

variable "run_seed" {
  description = "Run seed.sql after creating the DB (needs sqlcmd). Set false to just create the empty ShopFlow DB and seed it yourself in a GUI."
  type        = bool
  default     = true
}
