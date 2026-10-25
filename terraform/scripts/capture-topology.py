#!/usr/bin/env python3
"""Run on a Proxmox node: read-only, allowlisted fleet hardware snapshot, no secrets."""
import datetime
import json
import re
import subprocess


def read(path, *options):
    return json.loads(subprocess.check_output(
        ['pvesh', 'get', path, *options, '--output-format', 'json'], text=True))


names = {'tombstone', 'whyachi', 'biteforce', 'huge', 'minotaur', 'valkyrie', 'hydra', 'ubuntu-2404-template'}
fields = {'name', 'cores', 'sockets', 'memory', 'balloon', 'cpu', 'machine', 'bios', 'ostype',
          'scsihw', 'boot', 'onboot', 'agent', 'serial0', 'tags', 'startup', 'numa', 'template'}
result = {'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'vms': [], 'storage': []}
resources = read('/cluster/resources', '--type', 'vm')
result['other_guests'] = [{k: v for k, v in r.items() if k in {'name', 'vmid', 'node', 'type'}}
                          for r in resources if r.get('name') not in names]
for r in resources:
    if r.get('type') != 'qemu' or r.get('name') not in names:
        continue
    config = read(f"/nodes/{r['node']}/qemu/{r['vmid']}/config")
    safe = {k: v for k, v in config.items()
            if k in fields or re.fullmatch(r'(scsi|sata|virtio|ide|net|usb|hostpci)\d+', k)}
    result['vms'].append({'name': r['name'], 'vmid': r['vmid'], 'node': r['node'], 'config': safe})
for storage in read('/storage'):
    result['storage'].append({k: v for k, v in storage.items()
                              if k in {'storage', 'type', 'pool', 'path', 'content', 'nodes', 'shared'}})
print(json.dumps(result, indent=2, sort_keys=True))
