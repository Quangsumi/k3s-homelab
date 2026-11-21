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

data "coder_parameter" "repo_urls" {
  name         = "repo_urls"
  display_name = "Git repositories"
  description  = "Optional: one HTTPS or git@host:owner/repo.git URL per line, without credentials. Each repo needs a different name. New entries clone on restart; removing an entry never deletes files."
  type         = "string"
  form_type    = "textarea"
  default      = ""
  mutable      = true
  order        = 1
}

data "coder_parameter" "cpu" {
  name         = "cpu"
  display_name = "CPU limit"
  description  = "Shared by the editor, terminals and all repositories. Changes restart the workspace."
  type         = "string"
  form_type    = "dropdown"
  default      = "1"
  mutable      = true
  order        = 2
  option {
    name  = "0.5 CPU"
    value = "0.5"
  }
  option {
    name  = "1 CPU"
    value = "1"
  }
  option {
    name  = "2 CPUs"
    value = "2"
  }
  option {
    name  = "4 CPUs"
    value = "4"
  }
}

data "coder_parameter" "memory" {
  name         = "memory"
  display_name = "RAM limit"
  description  = "Shared by all tools and repositories. Start with 1 GiB; increase if builds or language servers run out of memory. Changes restart the workspace."
  type         = "string"
  form_type    = "dropdown"
  default      = "1"
  mutable      = true
  order        = 3
  option {
    name  = "1 GiB"
    value = "1"
  }
  option {
    name  = "2 GiB"
    value = "2"
  }
  option {
    name  = "4 GiB"
    value = "4"
  }
  option {
    name  = "8 GiB"
    value = "8"
  }
}

data "coder_parameter" "home_disk_size" {
  name         = "home_disk_size"
  display_name = "Home disk size"
  description  = "Persistent space shared by repositories, editor settings and caches. Choose at creation; this template does not resize existing disks."
  type         = "string"
  form_type    = "dropdown"
  default      = "5"
  mutable      = false
  order        = 4
  option {
    name  = "5 GiB"
    value = "5"
  }
  option {
    name  = "10 GiB"
    value = "10"
  }
  option {
    name  = "20 GiB"
    value = "20"
  }
  option {
    name  = "40 GiB"
    value = "40"
  }
}

variable "workspace_image" {
  type        = string
  description = "Image containing code-server, git and curl; user/home must be coder/1000 and /home/coder. Use a derived image for project toolchains."
  default     = "ghcr.io/coder/code-server:4.145.2"
}

locals {
  namespace  = "coder-workspaces"
  repo_root  = "/home/coder/repos"
  repo_urls  = [for line in split("\n", data.coder_parameter.repo_urls.value) : trimspace(line) if trimspace(line) != ""]
  repo_names = [for url in local.repo_urls : trimsuffix(basename(url), ".git")]
  labels = {
    "app.kubernetes.io/name" = "coder-workspace"
    "com.coder.workspace.id" = data.coder_workspace.me.id
    "com.coder.user.id"      = data.coder_workspace_owner.me.id
  }
}

resource "coder_agent" "main" {
  os                      = "linux"
  arch                    = "amd64"
  dir                     = local.repo_root
  startup_script_behavior = "blocking"
  env = {
    REPO_ROOT           = local.repo_root
    REPO_URLS           = join("\n", local.repo_urls)
    GIT_AUTHOR_NAME     = data.coder_workspace_owner.me.name
    GIT_AUTHOR_EMAIL    = data.coder_workspace_owner.me.email
    GIT_COMMITTER_NAME  = data.coder_workspace_owner.me.name
    GIT_COMMITTER_EMAIL = data.coder_workspace_owner.me.email
  }
  startup_script = file("${path.module}/startup.sh")
  lifecycle {
    precondition {
      condition     = alltrue([for url in local.repo_urls : can(regex("^(https://[A-Za-z0-9.-]+(:[0-9]+)?/|git@[A-Za-z0-9.-]+:)[A-Za-z0-9._/-]+/[A-Za-z0-9][A-Za-z0-9._-]*$", url))])
      error_message = "Enter one HTTPS or git@host:owner/repo.git URL per line, without credentials, spaces or query strings. Repository names must start with a letter or number."
    }
    precondition {
      condition     = length(distinct(local.repo_names)) == length(local.repo_names)
      error_message = "Repository folder names must be unique (including URLs with and without .git). For duplicate names, leave one out and clone it manually into a differently named folder."
    }
  }
  metadata {
    display_name = "CPU usage"
    key          = "0_cpu"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }
  metadata {
    display_name = "RAM usage"
    key          = "1_memory"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }
  metadata {
    display_name = "Home disk usage"
    key          = "2_disk"
    script       = "coder stat disk --path /home/coder"
    interval     = 60
    timeout      = 1
  }
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
  url          = "http://localhost:13337/?folder=${local.repo_root}"
  subdomain    = false
  share        = "owner"
  healthcheck {
    url       = "http://localhost:13337/healthz"
    interval  = 5
    threshold = 6
  }
}

module "zed" {
  source   = "registry.coder.com/coder/zed/coder"
  version  = "1.1.5"
  count    = data.coder_workspace.me.start_count
  agent_id = coder_agent.main.id
  folder   = local.repo_root
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
      requests = { storage = "${data.coder_parameter.home_disk_size.value}Gi" }
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
          pod_anti_affinity {
            preferred_during_scheduling_ignored_during_execution {
              weight = 1
              pod_affinity_term {
                topology_key = "kubernetes.io/hostname"
                label_selector {
                  match_expressions {
                    key      = "app.kubernetes.io/name"
                    operator = "In"
                    values   = ["coder-workspace"]
                  }
                }
              }
            }
          }
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
            requests = { cpu = "250m", memory = "512Mi" }
            limits   = { cpu = data.coder_parameter.cpu.value, memory = "${data.coder_parameter.memory.value}Gi" }
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
