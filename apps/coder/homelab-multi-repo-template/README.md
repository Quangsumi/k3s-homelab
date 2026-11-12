# Homelab multi-repo workspace

One workspace = one development pod + one persistent home volume. All repositories
share its CPU, RAM, tools and Git identity. Each repository keeps its own Git history.

## Publish through the Coder UI

1. Download `homelab-multi-repo-template.zip`, or create it from the repository root:

   ```bash
   python3 - <<'PY'
   from pathlib import Path
   from zipfile import ZipFile, ZIP_DEFLATED
   root = Path('apps/coder/template-multi-repo')
   with ZipFile('/tmp/homelab-multi-repo-template.zip', 'w', ZIP_DEFLATED) as archive:
       for name in ('main.tf', 'startup.sh', '.terraform.lock.hcl', 'README.md'):
           archive.write(root / name, name)
   PY
   ```

2. In **Templates → New template**, choose the ZIP upload option instead of the
   base-template builder. Upload the ZIP and name it **homelab-multi-repo**.
3. Complete the template build and create the template. Use this as a new template;
   it creates a new volume and does not move existing workspace files.
4. **Create workspace → homelab-multi-repo**. Name it `homelab` and choose:

   | Field | Choices | Default |
   | --- | --- | --- |
   | Git repositories | One URL per line; blank starts an empty workspace | Blank |
   | CPU limit | 0.5 / 1 / 2 / 4 CPUs | 1 CPU |
   | RAM limit | 1 / 2 / 4 / 8 GiB | 1 GiB |
   | Home disk size | 5 / 10 / 20 / 40 GiB | 5 GiB |

   Example **Git repositories**:

   ```text
   https://github.com/Quangsumi/k3s-homelab.git
   https://github.com/coder/code-server.git
   ```

5. Select **Create workspace**, then **VS Code Browser**. Both folders appear in
   the Explorer; **Source Control** lets you select, commit and push each repository.

```text
/home/coder/                  # Entire home lives on the same Longhorn PVC.
└── repos/                   # Browser, desktop VS Code and Zed open here.
    ├── k3s-homelab/.git/
    └── code-server/.git/
```

Optional: use **File → Add Folder to Workspace**, then **Save Workspace As**
`/home/coder/homelab.code-workspace` for a custom VS Code folder selection.

## Change resources or add repositories

- Open the workspace's **Settings → Parameters**, save changes, then restart when
  prompted. CPU/RAM and the repository list are editable; disk size is fixed at
  creation. Save files before restarting. An existing disk cannot be shrunk.
- Kubernetes requests stay at **250m CPU / 512 MiB RAM**. The dropdowns set upper
  limits, shared across all repositories; they do not reserve that much RAM/CPU.
- Add another URL to the list and restart to clone it. Existing folders are always
  preserved: no automatic pull, reset, remote changes or deletion. Removing a URL
  keeps its files. To change a repository's URL or use two repositories with the
  same final name, clone manually into another folder.
- You can also add a repository entirely inside VS Code: **Command Palette →
  Git: Clone**, enter its URL, select `/home/coder/repos`, then add/open the folder.
- Private repositories use SSH URLs such as
  `git@github.com:Quangsumi/private-repo.git`. First add the workspace owner's
  **Coder Git SSH key** to GitHub. Copy it from your Coder account settings,
  or run `coder publickey` from an authenticated CLI. Never
  put passwords or access tokens into this form.
- Clone failures appear in startup logs but still let you open the editor and
  terminal. Fix authentication and restart to retry.

## Open in Zed

The pinned `coder/zed` module adds a **Zed** button. Install Zed on your device;
it connects over SSH to `/home/coder/repos` in the same running pod.

One-time setup on **each device**, using a Coder CLI matching your server version:

```bash
coder login https://coder.lab
coder config-ssh
```

Then click **Zed** on the workspace and allow the browser to open it. Coder Desktop
can supply the SSH integration instead. Your device must trust the lab CA and reach
`coder.lab`. The button launches local Zed; it does not provide a browser Zed editor.

## Persistence and sizing

- **Stop** removes the pod, keeps the PVC and saved work. **Delete workspace**
  deletes its PVC. With this lab's `Retain` policy, the PV/Longhorn data remains
  until manually recovered or deleted; deleting a workspace does not free that disk.
- The 5 GiB volume holds **all** repositories, editor state and caches. Longhorn's
  configured two replicas use additional physical storage. Container image layers
  live on the node, outside this home volume.
- CPU, RAM and home-disk usage appear on the workspace page. Start small and raise
  limits as needed. Use separate workspaces when repositories need conflicting
  toolchains or independent restarts.
- One replica with `Recreate`; worker-only scheduling, optional spreading across
  workers, existing lab CA trust and the unprivileged workspace ServiceAccount are
  preserved. No Kubernetes API token or Docker socket is mounted into the workspace.

## Local checks (no cluster access)

```bash
terraform -chdir=apps/coder/template-multi-repo init -backend=false -lockfile=readonly
terraform -chdir=apps/coder/template-multi-repo fmt -check
terraform -chdir=apps/coder/template-multi-repo validate
terraform -chdir=apps/coder/template-multi-repo test
python3 -m unittest discover -s apps/coder/template-multi-repo/tests -v
```
