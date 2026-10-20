#!/bin/sh
# Runs on the VM, independently of the SSH connection.
set -eu
backup=$1
exec 9>"$backup/transaction.lock"
flock 9
# A successful controller check commits under this same lock.
[ ! -e "$backup/committed" ] || exit 0
[ -d "$backup/netplan" ] || exit 1
touch "$backup/rollback-started"
# Stop a delayed apply process before restoring files, so it cannot race recovery.
systemctl stop "ansible-network-${backup##*/}-apply.service" 2>/dev/null || true
find /etc/netplan -maxdepth 1 \( -type f -o -type l \) \( -name '*.yaml' -o -name '*.yml' \) -delete
cp -a "$backup/netplan/." /etc/netplan/
cloud_file=/etc/cloud/cloud.cfg.d/99-ansible-network.cfg
if [ -f "$backup/cloud-init.original" ]; then
    cp -a "$backup/cloud-init.original" "$cloud_file"
else
    rm -f "$cloud_file"
fi
/usr/sbin/netplan generate
/usr/sbin/netplan apply
touch "$backup/rolled-back"
