#!/usr/bin/env python3
"""Run on a Proxmox node BEFORE provisioning: read-only checks for an empty target."""
import json
import subprocess
import sys

def get(path, *args):
    return json.loads(subprocess.check_output(['pvesh', 'get', path, *args, '--output-format', 'json'], text=True))

fleet_ids = {100, 101, 104, 106, 108, 109, 111}
resources = get('/cluster/resources', '--type', 'vm')
collisions = [r for r in resources if r.get('vmid') in fleet_ids]
if collisions:
    print('FAIL: existing deployment IDs:', ', '.join(f"{r['vmid']}:{r.get('name')}" for r in collisions))
    print('This project is for an EMPTY target. Do not destroy or overwrite the live lab.')
    sys.exit(1)
for node, template_id in [('endgame', 9100), ('deepsix', 9101)]:
    config = get(f'/nodes/{node}/qemu/{template_id}/config')
    assert config.get('template') == 1, f'{template_id} is not a template'
    assert 'size=8G' in config.get('scsi0', '') or 'size=8192M' in config.get('scsi0', ''), 'Wrong template disk size'
    assert config.get('bios', 'seabios') == 'seabios', 'Firmware mismatch'
    assert 'enabled=1' in str(config.get('agent', '')) or str(config.get('agent', '')) == '1', 'Guest-agent channel missing'
    storage = get(f'/nodes/{node}/storage')
    available = {s['storage']: s for s in storage}
    for name in ['local-zfs', 'local-ssd', 'local']:
        assert name in available and available[name].get('active'), f'{node}/{name} not active'
    assert 'snippets' in available['local'].get('content', '').split(','), f'{node}/local needs snippets content'
print('PASS: target VM IDs are unused; expected Ubuntu templates/storage exist.')
print('STILL CHECK: LAN IP/MAC conflicts, DHCP pool, DNS .102, capacity, template boot test and NAS USB ownership.')
