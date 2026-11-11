terraform {
  required_version = ">= 1.9.0"
  required_providers {
    coder = {
      source  = "coder/coder"
      version = "2.20.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.38.0"
    }
  }
}

provider "coder" {}

# The built-in provisioner uses the coder/coder ServiceAccount in-cluster.
provider "kubernetes" {}

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

data "coder_parameter" "repo_url" {
  name         = "repo_url"
  display_name = "Git repository URL"
  description  = "HTTPS or SSH URL without embedded credentials. Clone once; existing files are never reset or pulled automatically."
  type         = "string"
  mutable      = false
}

variable "workspace_image" {
  type        = string
  description = "Image containing code-server, git and curl; user/home must be coder/1000 and /home/coder. Use a derived image for project toolchains."
  default     = "ghcr.io/coder/code-server:4.145.2"
}

locals {
  namespace = "coder-workspaces"
  labels = {
    "app.kubernetes.io/name" = "coder-workspace"
    "com.coder.workspace.id" = data.coder_workspace.me.id
    "com.coder.user.id"      = data.coder_workspace_owner.me.id
  }
}

resource "coder_agent" "main" {
  os                      = "linux"
  arch                    = "amd64"
  dir                     = "/home/coder/project"
  startup_script_behavior = "blocking"
  env = {
    REPO_URL            = data.coder_parameter.repo_url.value
    GIT_AUTHOR_NAME     = data.coder_workspace_owner.me.name
    GIT_AUTHOR_EMAIL    = data.coder_workspace_owner.me.email
    GIT_COMMITTER_NAME  = data.coder_workspace_owner.me.name
    GIT_COMMITTER_EMAIL = data.coder_workspace_owner.me.email
  }
  startup_script = <<-EOT
    set -eu
    if [ ! -d /home/coder/project/.git ]; then
      git clone -- "$REPO_URL" /home/coder/project
    fi
    # Only Coder can reach this listener; Coder supplies authentication.
    code-server --auth none --bind-addr 127.0.0.1:13337 --disable-telemetry \
      /home/coder/project >/tmp/code-server.log 2>&1 &
  EOT
  display_apps {
    vscode       = true
    web_terminal = true
    ssh_helper   = true
  }
}

resource "coder_app" "browser" {
  agent_id     = coder_agent.main.id
  slug         = "code-server"
  display_name = "VS Code Browser"
  icon         = "/icon/code.svg"
  url          = "http://localhost:13337/?folder=/home/coder/project"
  subdomain    = false
  share        = "owner"
  healthcheck {
    url       = "http://localhost:13337/healthz"
    interval  = 5
    threshold = 6
  }
}

# No start_count: stopping a workspace removes compute, not its home directory.
resource "kubernetes_persistent_volume_claim_v1" "home" {
  metadata {
    name      = "coder-${data.coder_workspace.me.id}-home"
    namespace = local.namespace
    labels    = local.labels
  }
  wait_until_bound = false
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "longhorn"
    resources {
      requests = { storage = "20Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "workspace" {
  count            = data.coder_workspace.me.start_count
  wait_for_rollout = false
  metadata {
    name      = "coder-${data.coder_workspace.me.id}"
    namespace = local.namespace
    labels    = local.labels
  }
  spec {
    replicas = 1
    strategy { type = "Recreate" }
    selector { match_labels = local.labels }
    template {
      metadata { labels = local.labels }
      spec {
        service_account_name            = "coder-workspace"
        automount_service_account_token = false
        priority_class_name             = "homelab-dev"
        node_selector                   = { "kubernetes.io/arch" = "amd64" }
        security_context {
          run_as_non_root = true
          run_as_user     = 1000
          run_as_group    = 1000
          fs_group        = 1000
          seccomp_profile { type = "RuntimeDefault" }
        }
        affinity {
          node_affinity {
            required_during_scheduling_ignored_during_execution {
              node_selector_term {
                match_expressions {
                  key      = "node-role.kubernetes.io/control-plane"
                  operator = "DoesNotExist"
                }
                match_expressions {
                  key      = "node-role.kubernetes.io/master"
                  operator = "DoesNotExist"
                }
              }
            }
          }
        }
        container {
          name              = "dev"
          image             = var.workspace_image
          image_pull_policy = "IfNotPresent"
          # Bootstrap and agent traffic stay inside the cluster, independent of
          # client-side .lab DNS/Tailscale reachability.
          command = ["sh", "-c", replace(coder_agent.main.init_script, data.coder_workspace.me.access_url, "http://coder.coder.svc.cluster.local")]
          env {
            name  = "CODER_AGENT_TOKEN"
            value = coder_agent.main.token
          }
          env {
            name  = "SSL_CERT_FILE"
            value = "/etc/homelab/trust/ca-bundle.pem"
          }
          env {
            name  = "CURL_CA_BUNDLE"
            value = "/etc/homelab/trust/ca-bundle.pem"
          }
          env {
            name  = "GIT_SSL_CAINFO"
            value = "/etc/homelab/trust/ca-bundle.pem"
          }
          security_context {
            allow_privilege_escalation = false
            capabilities { drop = ["ALL"] }
          }
          resources {
            requests = { cpu = "1", memory = "2Gi" }
            limits   = { cpu = "2", memory = "4Gi" }
          }
          volume_mount {
            name       = "home"
            mount_path = "/home/coder"
          }
          volume_mount {
            name       = "homelab-trust"
            mount_path = "/etc/homelab/trust"
            read_only  = true
          }
        }
        volume {
          name = "home"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.home.metadata[0].name
          }
        }
        volume {
          name = "homelab-trust"
          config_map { name = "coder-trust-bundle" }
        }
      }
    }
  }
}
