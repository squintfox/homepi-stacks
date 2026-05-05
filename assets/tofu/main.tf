terraform {
  required_providers {
    portainer = {
      source  = "portainer/portainer"
      version = "~> 1.0"
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
resource "portainer_stack" "assets" {
  # EDIT: 
  name            = "assets"
  deployment_type = "swarm"
  method          = "repository"
  endpoint_id     = data.portainer_environment.swarm.id

  repository_url            = var.HPI_STACKS_REPO_URL
  repository_reference_name = "refs/heads/release"
  # EDIT: 
  file_path_in_repository   = "assets/docker-compose.yml"

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
    name  = "HPI_PRIMARY_EMAIL"
    value = var.HPI_PRIMARY_EMAIL
  }
  env {
    name  = "SNIPE_APP_KEY"
    value = var.SNIPE_APP_KEY
  }
  env {
    name  = "SNIPE_DB_DATABASE"
    value = var.SNIPE_DB_DATABASE
  }
  env {
    name  = "SNIPE_DB_USERNAME"
    value = var.SNIPE_DB_USERNAME
  }
  env {
    name  = "SNIPE_DB_PASSWORD"
    value = var.SNIPE_DB_PASSWORD
  }

  lifecycle {
    ignore_changes = [repository_reference_name]
  }
}
