# AI Reliability Lab - Terraform Infrastructure

provider "kubernetes" {
  config_path = "~/.kube/config"
}

# Namespace
resource "kubernetes_namespace" "reliability_lab" {
  metadata {
    name = "reliability-lab"
  }
}

# ConfigMap for environment variables
resource "kubernetes_config_map" "reliability_config" {
  metadata {
    name      = "reliability-config"
    namespace = kubernetes_namespace.reliability_lab.metadata[0].name
  }

  data = {
    "CLICKHOUSE_HOST" = "clickhouse-service"
    "CLICKHOUSE_PORT" = "8123"
    "REDIS_URL"       = "redis://redis-service:6379/0"
    "ENVIRONMENT"     = "production"
  }
}
