variable "HPI_PORTAINER_TOKEN" {
  description = "Portainer API key (generate under User > API keys)"
  type        = string
  sensitive   = true
}
variable "HPI_DNS_DOMAIN" {
  type        = string
}
variable "HPI_HTTPS_PORT" {
  type        = string
}
variable "HPI_STACKS_REPO_URL" {
  type        = string
}
variable "HPI_LOCAL_DATA_PATH" {
  type        = string
}

# /required

variable "HPI_DESEC_TOKEN" {
  type        = string
}
variable "HPI_TIME_ZONE" {
  type        = string
}
variable "HPI_PRIMARY_EMAIL" {
  type        = string
}
variable "SNIPE_APP_KEY" {
  type        = string
  sensitive   = true
}
variable "SNIPE_DB_DATABASE" {
  type        = string
}
variable "SNIPE_DB_USERNAME" {
  type        = string
}
variable "SNIPE_DB_PASSWORD" {
  type        = string
  sensitive   = true
}
