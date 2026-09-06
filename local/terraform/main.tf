terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.75.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "minioadmin"
  secret_key                  = "minioadmin"
  s3_force_path_style         = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3 = "http://localhost:9002"
  }
}

resource "aws_s3_bucket" "my_bucket1" {
  bucket = "source"
}

resource "aws_s3_bucket" "my_bucket2" {
  bucket = "target"
}
