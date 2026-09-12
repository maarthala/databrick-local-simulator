variable "subscription_id" {
  description = "Azure subscription id. Leave empty to use ARM_SUBSCRIPTION_ID from the environment. Get it with: az account show --query id -o tsv"
  type        = string
  default     = ""
}

variable "location" {
  description = "Azure region for the dev environment."
  type        = string
  default     = "swedencentral"
}

variable "resource_group_name" {
  description = "Resource group to create for the ADF dev SQL environment (its own, separate from base-setup)."
  type        = string
  default     = "rg-adf-sql"
}

variable "prefix" {
  description = "Static naming prefix for all resources (e.g. 'epireum'). Match base-setup. Server becomes <prefix>-sql — must be GLOBALLY UNIQUE across Azure."
  type        = string
  default     = "epireum"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,20}$", var.prefix))
    error_message = "prefix: 3-21 lowercase letters/digits, starting with a letter."
  }
}

variable "sql_admin_login" {
  description = "SQL Server administrator login name."
  type        = string
  default     = "sqladmin"
}

variable "sql_admin_password" {
  description = "SQL Server administrator password. Default provided for dev/learning — CHANGE it for anything real (set in terraform.tfvars or export TF_VAR_sql_admin_password). Azure requires 8-128 chars with 3 of: uppercase, lowercase, digit, symbol."
  type        = string
  sensitive   = true
  default     = "qwert@123456"

  validation {
    condition     = length(var.sql_admin_password) >= 12
    error_message = "Use at least 12 characters for the SQL admin password."
  }
}

variable "sql_database_name" {
  description = "Name of the database to create (the source DB ADF will read/write)."
  type        = string
  default     = "shopflow"
}

variable "sku_name" {
  description = "Azure SQL Database SKU. 'Basic' (~5 DTU, cheapest, ~US$5/mo) is fine for dev; 'S0'/'S1' for more headroom; 'GP_S_Gen5_1' for serverless (auto-pause)."
  type        = string
  default     = "Basic"
}

variable "max_size_gb" {
  description = "Max database size in GB (Basic tier caps at 2)."
  type        = number
  default     = 2
}

variable "allow_azure_services" {
  description = "Add a firewall rule allowing Azure services (0.0.0.0) to reach the server — needed for Azure Data Factory to connect with the default runtime."
  type        = bool
  default     = true
}

variable "allow_all_internet" {
  description = "Open the SQL server firewall to ALL public IPs (0.0.0.0-255.255.255.255). INSECURE — dev/learning only; connections still need the SQL login."
  type        = bool
  default     = true
}

variable "client_ip" {
  description = "Your workstation's public IP, to allow connecting from SSMS / Azure Data Studio / sqlcmd. Leave empty to skip. Find it with: curl -s ifconfig.me"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    environment = "dev"
    project     = "adf-training"
    managed_by  = "terraform"
  }
}
