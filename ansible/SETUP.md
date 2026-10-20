# Prepare Windows to run Ansible

This page prepares your laptop. It does not log into or change a VM.

## 1. Open Ubuntu

Search the Windows Start menu for **Ubuntu** and open it.
If it opens a terminal, continue to step 2.

If Ubuntu is not installed, open **PowerShell as administrator** and run:

```powershell
wsl --install -d Ubuntu
```

This installs Ubuntu inside Windows. Restart Windows if requested, then open Ubuntu.
The first launch asks you to create a Linux username and password. Those belong to
Ubuntu on your laptop; they are not VM credentials. While typing a Linux password,
no dots or stars may appear. That is normal.

## 2. Install the tools Ansible needs

**Where: Ubuntu terminal.**

```bash
sudo apt update
```

`sudo` means run with administrator permission inside Ubuntu. It asks for your
Ubuntu password. `apt update` refreshes the list of available software.

Next:

```bash
sudo apt install -y python3 python3-venv openssh-client sshpass
```

This installs:

- `python3`: the language Ansible runs on.
- `python3-venv`: a way to keep Ansible's software in its own folder.
- `openssh-client`: the SSH program used to connect to VMs.
- `sshpass`: supports supplying a VM password to SSH when needed.

`-y` accepts the package installation prompt.

Check Python:

```bash
python3 --version
```

These project requirements need Python 3.11 or newer. If you have an older version,
use a newer supported Ubuntu release before continuing.

## 3. Open this project's folder

**Where: Ubuntu terminal.**

```bash
cd '/mnt/d/OneDrive/Desktop/Side Quests/PETs/k3s-homelab/ansible'
```

`cd` means change folder. Ubuntu sees the Windows D: drive as `/mnt/d`.
The quotes keep spaces in the folder name together.

```bash
pwd
```

This prints your current folder. It should end in `k3s-homelab/ansible`.

## 4. Give Ansible its own installation folder

```bash
python3 -m venv ~/.venvs/homelab-ansible
```

This creates a folder holding Ansible's Python tools. `~` means your Ubuntu home
folder. It keeps these tools separate from Ubuntu's own Python packages.

```bash
source ~/.venvs/homelab-ansible/bin/activate
```

This tells the current terminal to use that installation folder.
Your prompt may now start with `(homelab-ansible)`.

## 5. Install Ansible

```bash
python -m pip install -r requirements.txt
```

`pip` installs Python software. `-r requirements.txt` means read the software list
from that file. The list contains Ansible and a tool for checking Ansible files.

Then:

```bash
ansible-galaxy collection install -r requirements.yml
```

This installs the extra Ansible tools listed in `requirements.yml`.
We need one of them to manage SSH keys. Ansible calls a bundle of extra tools a **collection**.
The similar filenames have different purposes: `.txt` installs Python programs;
`.yml` installs Ansible collections.

## 6. Select our project settings

```bash
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
```

This tells Ansible to use the settings in this folder's `ansible.cfg`.
`$PWD` means your current folder. We select the file explicitly because Ubuntu may
otherwise skip settings stored on a Windows-mounted folder.

```bash
ansible --version
```

**Expected result:** version information appears, and its `config file` line points
to this project's `ansible.cfg`. If it says `None`, check your current folder and
repeat the export command.

Return to [the first exercise](LESSONS.md#4-find-your-laptops-public-key).

## When you open a new Ubuntu terminal later

Installation is done once. These commands prepare each new terminal:

```bash
source ~/.venvs/homelab-ansible/bin/activate
cd '/mnt/d/OneDrive/Desktop/Side Quests/PETs/k3s-homelab/ansible'
export ANSIBLE_CONFIG="$PWD/ansible.cfg"

export ANSIBLE_SSH_COMMON_ARGS='-o StrictHostKeyChecking=accept-new'
```

They choose the installed tools, open the project, and select its settings.
