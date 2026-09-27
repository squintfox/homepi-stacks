terraform {
  required_providers {
    portainer = {
      source  = "portainer/portainer"
      version = "~> 1.0"
    }
  }

  encryption {
    key_provider "pbkdf2" "tfstate" {
      passphrase = var.HPI_TFSTATE_PASSPHRASE
    }

    method "aes_gcm" "tfstate" {
      keys = key_provider.pbkdf2.tfstate
    }

    method "unencrypted" "migrate" {}

    state {
      method = method.aes_gcm.tfstate

      fallback {
        method = method.unencrypted.migrate
      }
    }
  }
}

provider "portainer" {
  endpoint = "https://manage.${var.HPI_DNS_DOMAIN}:${var.HPI_HTTPS_PORT}"
  api_key  = var.HPI_PORTAINER_TOKEN
}

data "portainer_environment" "swarm" {
  name = "local-swarm"
}

# EDIT: 
resource "portainer_stack" "budget" {
  # EDIT: 
  name            = "budget"
  deployment_type = "swarm"
  method          = "repository"
  endpoint_id     = data.portainer_environment.swarm.id

  repository_url            = var.HPI_STACKS_REPO_URL
  repository_reference_name = "refs/heads/release"
  # EDIT: 
  file_path_in_repository   = "budget/docker-compose.yml"

  git_repository_authentication = false
  prune                         = true

  # EDIT: 
  env {
    name  = "HPI_LOCAL_DATA_PATH"
    value = var.HPI_LOCAL_DATA_PATH
  }
  env {
    name  = "HPI_DNS_DOMAIN"
    value = var.HPI_DNS_DOMAIN
  }
  env {
    name  = "HPI_HTTPS_PORT"
    value = var.HPI_HTTPS_PORT
  }

  # /required
  env {
    name  = "HPI_DESEC_TOKEN"
    value = var.HPI_DESEC_TOKEN
  }
  env {
    name  = "HPI_TIME_ZONE"
    value = var.HPI_TIME_ZONE
  }
  env {
    name  = "ACTUAL_BUDGET_SYNC_ID"
    value = var.ACTUAL_BUDGET_SYNC_ID
  }
  env {
    name  = "ACTUAL_BUDGET_PASSWORD"
    value = var.ACTUAL_BUDGET_PASSWORD
  }
  env {
    name  = "ACTUAL_API_PASSWORD"
    value = var.ACTUAL_API_PASSWORD
  }
  env {
    name  = "ACTUAL_OPENID_CLIENT_USERNAME"
    value = var.ACTUAL_OPENID_CLIENT_USERNAME
  }
  env {
    name  = "ACTUAL_OPENID_CLIENT_SECRET"
    value = var.ACTUAL_OPENID_CLIENT_SECRET
  }

  lifecycle {
    ignore_changes = [repository_reference_name]
  }
}
