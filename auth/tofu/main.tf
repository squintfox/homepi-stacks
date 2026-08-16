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

resource "portainer_stack" "auth" {
  name            = "auth"
  deployment_type = "swarm"
  method          = "repository"
  endpoint_id     = data.portainer_environment.swarm.id

  repository_url            = var.HPI_STACKS_REPO_URL
  repository_reference_name = "refs/heads/release"
  file_path_in_repository   = "auth/docker-compose.yml"

  git_repository_authentication = false
  prune                         = true

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
    name  = "HPI_AUTH_SESSION_SECRET"
    value = var.HPI_AUTH_SESSION_SECRET
  }
  env {
    name  = "HPI_AUTH_JWT_SECRET"
    value = var.HPI_AUTH_JWT_SECRET
  }
  env {
    name  = "HPI_AUTH_STORAGE_ENCRYPTION_KEY"
    value = var.HPI_AUTH_STORAGE_ENCRYPTION_KEY
  }

  lifecycle {
    ignore_changes = [repository_reference_name]
  }
}
