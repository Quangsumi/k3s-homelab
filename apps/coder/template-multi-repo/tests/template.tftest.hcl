# Mock both providers: these plans cannot read or modify the cluster or Coder.
mock_provider "coder" {}
mock_provider "kubernetes" {}

override_data {
  target = data.coder_workspace.me
  values = {
    id          = "11111111-1111-4111-8111-111111111111"
    name        = "homelab"
    start_count = 1
    access_url  = "https://coder.lab"
  }
}
override_data {
  target = data.coder_workspace_owner.me
  values = {
    id    = "22222222-2222-4222-8222-222222222222"
    name  = "developer"
    email = "developer@example.com"
  }
}
override_data {
  target = data.coder_parameter.repo_urls
  values = { value = "" }
}
override_data {
  target = data.coder_parameter.cpu
  values = { value = "1" }
}
override_data {
  target = data.coder_parameter.memory
  values = { value = "1" }
}
override_data {
  target = data.coder_parameter.home_disk_size
  values = { value = "5" }
}

run "small_workspace" {
  command = plan
  assert {
    condition     = kubernetes_persistent_volume_claim_v1.home.spec[0].resources[0].requests.storage == "5Gi"
    error_message = "The small workspace must request a 5 GiB home volume."
  }
  assert {
    condition     = kubernetes_deployment_v1.workspace[0].spec[0].template[0].spec[0].container[0].resources[0].limits == tomap({ cpu = "1", memory = "1Gi" })
    error_message = "The small workspace must use 1 CPU and 1 GiB limits."
  }
}

run "larger_multi_repo_workspace" {
  command = plan
  override_data {
    target = data.coder_parameter.repo_urls
    values = { value = "  https://github.com/example/frontend.git\r\n\n git@gitlab.example.com:team/backend.git \n" }
  }
  override_data {
    target = data.coder_parameter.cpu
    values = { value = "4" }
  }
  override_data {
    target = data.coder_parameter.memory
    values = { value = "8" }
  }
  override_data {
    target = data.coder_parameter.home_disk_size
    values = { value = "40" }
  }
  assert {
    condition     = coder_agent.main.env.REPO_URLS == "https://github.com/example/frontend.git\ngit@gitlab.example.com:team/backend.git"
    error_message = "Normalize pasted Windows line endings, whitespace and blank lines before cloning."
  }
  assert {
    condition     = kubernetes_deployment_v1.workspace[0].spec[0].template[0].spec[0].container[0].resources[0].limits == tomap({ cpu = "4", memory = "8Gi" })
    error_message = "Resource choices must reach the container limits."
  }
  assert {
    condition     = kubernetes_persistent_volume_claim_v1.home.spec[0].resources[0].requests.storage == "40Gi"
    error_message = "Disk choices must reach the PVC."
  }
}

run "stopped_workspace_keeps_home" {
  command = plan
  override_data {
    target = data.coder_workspace.me
    values = {
      id          = "11111111-1111-4111-8111-111111111111"
      name        = "homelab"
      start_count = 0
      access_url  = "https://coder.lab"
    }
  }
  assert {
    condition     = length(kubernetes_deployment_v1.workspace) == 0 && kubernetes_persistent_volume_claim_v1.home.metadata[0].name == "coder-11111111-1111-4111-8111-111111111111-home"
    error_message = "Stopping must remove compute while keeping the same PVC."
  }
}

run "reject_folder_collision" {
  command = plan
  override_data {
    target = data.coder_parameter.repo_urls
    values = { value = "https://github.com/team-one/api.git\ngit@github.com:team-two/api" }
  }
  expect_failures = [coder_agent.main]
}

run "reject_embedded_credentials" {
  command = plan
  override_data {
    target = data.coder_parameter.repo_urls
    values = { value = "https://user:token@github.com/team/private.git" }
  }
  expect_failures = [coder_agent.main]
}

run "reject_shell_input" {
  command = plan
  override_data {
    target = data.coder_parameter.repo_urls
    values = { value = "https://github.com/team/repo.git;touch /tmp/injected" }
  }
  expect_failures = [coder_agent.main]
}
