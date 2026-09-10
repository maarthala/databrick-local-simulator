terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  # azurerm v4 requires an explicit subscription id. Set it via the variable, or
  # export ARM_SUBSCRIPTION_ID and leave the variable empty.
  subscription_id = var.subscription_id != "" ? var.subscription_id : null
  features {}
}
