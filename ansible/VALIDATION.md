# Automated Ubuntu DNS changes - October 20, 2026

* Replaced network-stage.yml and its minimal template with network.yml and one
  VM-local rollback script. Normal runs back up, validate, apply and verify DNS
  changes without manual SSH commands. No VM was contacted or changed here.
* Preserves effective Netplan addressing, routes, IPv6, interface naming and search
  domains. Does not convert DHCP to static or change addresses. Hydra/OMV excluded.
* The rollback timer is armed before live changes. Apply runs independently of SSH;
  fresh connectivity, IP/gateway, effective DNS, uncached resolution and local K3s
  readiness checks must pass before commit. Timer/commit share a lock to avoid races.
* PASS: 18 offline regression tests. DNS fixtures cover recursive preservation of
  existing settings, MAC-based interface matching, unexpected addresses/OS rejection
  and independence of SSH DNS names from network addresses.
* PASS: 17 public YAML parses with duplicate-key rejection, embedded Jinja syntax,
  local document links and rollback script UTF-8/LF format. Secrets excluded.
* NOT RUN: native Ansible syntax/lint, shell execution, Netplan validation or real
  systemd timer/SSH/Kubernetes integration. WSL and Git Bash execution were denied
  in this session; parser/fixture results do not establish live recovery behavior.
* A transient timer cannot survive reboot or fix a frozen VM. The guide retains
  Proxmox console access as recovery fallback and starts with Valkyrie only.

Earlier entries below describe the project at their respective dates.

# Local validation — October 17, 2026

## Simplified Proxmox agent option — October 20, 2026

* Replaced the larger name-lookup implementation and its helper with one four-task
  playbook: discover current cluster placement by inventory VM ID, read settings,
  verify the expected name/options, and enable the agent option if disabled.
* Select guest aliases with normal --limit valkyrie,huge; commands run through
  Endgame by default (proxmox_host can select another SSH entry host). No target_vm
  or vm_names argument is required. No VM owner is hardcoded in inventory.
* IDs and exact lowercase names match the supplied screenshot: tombstone 100,
  whyachi 101, huge 104, minotaur 106, hydra 108, valkyrie 109, biteforce 111.
  Template 105 and Tailscale container 103 were not added to the guest inventory.
* Local fixtures cover screenshot IDs, placement changes, missing IDs, identity,
  template/lock/custom-option guards, and skipping already-enabled agent settings.
* Public YAML/Jinja and document-link checks passed. Ansible-native execution and
  live Proxmox commands were not run; no VMs or account settings were changed.



## Explicit Vault loading — October 19, 2026



* Existing encrypted credentials moved to secrets/vault.yml, with matching ciphertext

  checksums. The old automatic inventory location is absent; Git ignores the new path.

* No conditional loading code, empty-variable file or use_vault switch remains.

  Jobs needing secrets use Ansible's built-in `-e @secrets/vault.yml --ask-vault-pass`.

  Key-only jobs need neither flag. Guides and command examples updated accordingly.

* Local regression tests and public YAML/Jinja/document-link checks passed. Real

  Ansible execution remains untested because WSL access is denied in this session.

* No secrets decrypted or displayed, and no VM changes or remote connections made.



## Separate SSH DNS names from static IPv4 addresses — October 19, 2026



* Every guest now has an explicit numeric network_address in inventory. Existing

  ansible_host values were preserved; users can switch them to working DNS names.

* Removed the shared network_address derivation from ansible_host. Network staging

  now checks that network_address is already in the guest's gathered IPv4 addresses,

  independently of the SSH endpoint, preserving the existing-IP requirement.

* Updated the naming, network and technical guides with the two separate settings.

* PASS: 21 offline tests, including DNS/IP endpoints producing identical Netplan,

  rejecting DNS names as network addresses, and rejecting missing/unassigned IPs.

* YAML parsing, duplicate-key checks, Jinja parsing and local document links passed.

  The real Vault file was excluded and not read.

* NOT RUN: Ansible syntax/lint, DNS lookups from Ubuntu, Netplan validation or remote

  execution. No VM settings, DNS records, private keys or encrypted credentials changed.



## Simplified Biteforce exception — October 19, 2026



* Current Biteforce settings use ansible_password: null to override the shared

  bootstrap password expression. Removed ssh_password_login and custom SSH options.

* Kept the confirmed username/key path and Hydra's nas_appliances exclusions.

* Updated the guide and tests. PASS: 16 offline tests, 19 YAML parses with duplicate-key

  rejection, embedded Jinja parsing and local Markdown links.

* The precedence test models host settings overriding group settings; it is not

  execution by Ansible's inventory engine. No VM connections or changes performed.

* The earlier exception implementation below is historical and has been superseded.



## Hydra/OpenMediaVault and Biteforce/key-only exceptions — October 19, 2026



* Hydra now has a host override selecting its existing root account. It is grouped

  under nas_appliances, which baseline, root-access and network-stage explicitly

  exclude. Key management and read-only playbooks still include it.

* Biteforce selects biteforce and ~/.ssh/homelab_laptop, with client password and

  keyboard-interactive authentication disabled. Its Vault SSH password is not read,

  even when bootstrap_password_auth=true for the rest of the inventory.

* USER-VERIFIED: the user supplied a successful WSL SSH login using that Biteforce

  account/key. This establishes the selected direct login, not Ansible integration.

* PASS: all 19 local YAML files parsed, duplicate-key checks, embedded Jinja parsing

  and local Markdown links; 16 offline tests passed, including the new exceptions.

* NOT RUN BY THIS AGENT: remote SSH/Ansible jobs or VM changes. No encrypted Vault

  contents were edited. Hydra's stored SSH password must correspond to root.



## Existing user accounts and optional root access — October 19, 2026



* Guest logins now default to their stable VM alias as username. Key tasks edit the

  login user's own keys with become=false. Proxmox host logins remain separately configured.

* Administrative guest tasks continue to use sudo; per-VM sudo passwords are read

  from Vault independently of whether SSH uses a password or key.

* Added the separate root-access.yml and ROOT-ACCESS.md: existing-user sudo -> root

  keys -> root password hash -> root-only SSH policy -> fresh key-only root login.

* Root SSH defaults to permitting both key and password in this dedicated job. The

  optional root_ssh_password_login=false setting selects key-only SSH instead.

* SSH configuration is validated before reload; failure of effective policy or the

  new root connection restores the previous SSH configuration. Added root keys and

  the root password are deliberately not rolled back. No full transaction is claimed.

* PASS: all 16 YAML files parsed, duplicate-key rejection, embedded Jinja parsing,

  and local Markdown file links.

* PASS: 14 offline tests, including user-account defaults, key tasks without sudo,

  sudo credentials with key SSH, root hash guards/log suppression, root-only SSH

  policy rendering, and the earlier VM-name discovery cases.

* NOT RUN: Ansible syntax/lint, real sshd validation, SSH reload or account changes,

  target sudo permissions, key/password authentication, or remote integration.

* The public key file exists, but inventory/group_vars/all/vault.yml was absent at

  preparation time. No VM was contacted or changed.



## Stable VM names — October 19, 2026



* Removed stored VM IDs and numbered aliases from active inventory, password examples

  and lesson commands. Exact `proxmox_name` values follow the lab labels and still need

  confirming against the UI; no live name discovery was performed during editing.

* The Proxmox job queries cluster resources through one selected entry host, requires

  one exact QEMU name match, discovers the current ID/node, checks config identity,

  refreshes placement before changing settings, and sends the config digest on update.

* PASS: 8 offline tests using the actual YAML selector and guard expressions, covering

  changed IDs/hosts between runs, missing/wrong-case names, duplicate names, LXC exclusion,

  templates, locks, mid-run relocation, config identity/options/digest requirements,

  and stable inventory aliases without stored VM IDs.

* PASS: 13 YAML files parsed, duplicate-key checks, embedded Jinja parsing, local

  Markdown file links. These are parser/fixture checks, not Ansible integration checks.

* NOT RUN: Ansible syntax/lint, live Proxmox API, intra-cluster routing, or VM changes.

* Test command on a Linux controller with PyYAML and Jinja2 installed:

  `python -m unittest discover -s tests -p 'test_*.py'` (from the ansible directory).



The earlier entries below record validation at the time of those changes.



* PASS: all 10 YAML files parsed with PyYAML, rejecting duplicate mapping keys.

* PASS: Jinja syntax parsed in YAML string values.

* PASS: Netplan template rendered with representative inputs and parsed as YAML;

  expected address 192.168.63.22/24 was checked.

* PASS: source review separates guest and Proxmox targets, preserves unrelated SSH

  keys, and stages network configuration outside /etc/netplan.

* NOT RUN: ansible-playbook --syntax-check and ansible-lint. No usable Ansible Linux

  controller was available; WSL enumeration returned Wsl/E_ACCESSDENIED.

* NOT RUN: Netplan schema validation; Netplan is not installed in this Windows session.

* NOT RUN: remote connectivity, guest OS discovery, guest-agent integration, network

  activation or Kubernetes health checks. No VM was contacted or changed.



Parser checks are not a substitute for Ansible syntax checks or target integration.

Local parser dependencies are in ignored .validation/ and are not runtime requirements

for the Ansible project. Controller installation is documented in LESSONS.md.



## Guide rewrite — October 19, 2026



* Replaced the first lesson with one VM, one job, password prompts and explicit

  instructions for where each command runs and what success looks like.

* Added SETUP.md and NEXT-STEPS.md; moved technical project details to REFERENCE.md.

* Added a separate beginner inventory/playbook so the first exercise does not load

  the full inventory's password expressions or require an existing Vault file.

* PASS: all 12 project YAML files parsed with duplicate-key rejection; embedded

  Jinja syntax parsed; beginner inventory contains only Valkyrie.

* PASS: local Markdown file links in the top-level guides resolve.

* NOT RUN: Ansible syntax checks and remote execution. These document edits do not

  establish that the recorded VM address, root login or password access work today.

