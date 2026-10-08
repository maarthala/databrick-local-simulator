# Fabric control-plane only. We deliberately do NOT use azurerm here, so this
# module can never create a billable Fabric capacity (azurerm_fabric_capacity).
# Everything below runs on your EXISTING (free Trial) capacity → apply/destroy
# freely with no cost.
terraform {
  required_version = ">= 1.11" # write-only + ephemeral (GitHub token)
  required_providers {
    fabric = {
      source  = "microsoft/fabric"
      version = ">= 1.0" # `terraform init` resolves the current release
    }
  }
}

# Auth uses your `az login` session by default (same identity you use in the
# Fabric portal) — no secrets in code. For CI, set a service principal via the
# FABRIC_* / ARM_* env vars and enable the tenant setting
# "Service principals can use Fabric APIs".
provider "fabric" {
  # tenant_id = var.tenant_id  # optional; taken from az login if omitted
}
