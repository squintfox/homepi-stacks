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

resource "portainer_stack" "update" {
  name            = "update"
  deployment_type = "swarm"
  method          = "repository"
  endpoint_id     = data.portainer_environment.swarm.id
  update_interval = "168h"  # 7 days
  force_update    = false

  repository_url            = var.HPI_STACKS_REPO_URL
  repository_reference_name = "refs/heads/release"
  file_path_in_repository   = "update/docker-compose.yml"

  git_repository_authentication = false
  prune                         = true

  env {
    name  = "HPI_TIME_ZONE"
    value = var.HPI_TIME_ZONE
  }
  env {
    name  = "SHEPHERD_REGISTRY_USERNAME"
    value = var.SHEPHERD_REGISTRY_USERNAME
  }
  env {
    name  = "SHEPHERD_REGISTRY_PASSWORD"
    value = var.SHEPHERD_REGISTRY_PASSWORD
  }

  lifecycle {
    ignore_changes = [env, repository_reference_name]
  }
}
