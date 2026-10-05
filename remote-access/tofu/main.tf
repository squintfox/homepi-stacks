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
resource "portainer_stack" "remote-access" {
  # EDIT: 
  name            = "remote-access"
  deployment_type = "swarm"
  method          = "repository"
  endpoint_id     = data.portainer_environment.swarm.id

  repository_url            = var.HPI_STACKS_REPO_URL
  repository_reference_name = "refs/heads/release"
  # EDIT: 
  file_path_in_repository   = "remote-access/docker-compose.yml"

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

  env {
    name  = "HPI_TAILSCALE_AUTHKEY"
    value = var.HPI_TAILSCALE_AUTHKEY
  }
  env {
    name  = "HPI_SUBNET"
    value = var.HPI_SUBNET
  }

  lifecycle {
    ignore_changes = [repository_reference_name]
  }
}
