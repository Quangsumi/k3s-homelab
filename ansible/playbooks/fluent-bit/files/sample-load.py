"""Read a small before/after load sample. Never reads logs, configuration or tokens."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request


def pressure_total(name):
    """Linux counts microseconds when all active tasks were stalled."""
    lines = Path('/proc/pressure/' + name).read_text().splitlines()
    full = next(line for line in lines if line.startswith('full '))
    return int(full.split('total=')[1])


def snapshot():
    status = subprocess.check_output(
        ['systemctl', 'show', 'fluent-bit', '-p', 'MainPID', '-p', 'ActiveState'], text=True
    )
    service = dict(line.split('=', 1) for line in status.splitlines())
    if service['ActiveState'] != 'active' or service['MainPID'] == '0':
        raise RuntimeError('Fluent Bit must be running before a rollout load sample')
    process = Path('/proc') / service['MainPID']
    fields = (process / 'stat').read_text().rpartition(') ')[2].split()
    request = urllib.request.Request(
        'http://127.0.0.1:2021/api/v1/metrics', headers={'User-Agent': 'agent-local'}
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        metrics = json.load(response)
    return {
        'time': time.monotonic(),
        'pid': service['MainPID'],
        'cpu': (int(fields[11]) + int(fields[12])) / os.sysconf('SC_CLK_TCK'),
        'io': {key: int(value) for key, value in
               (line.split(':') for line in (process / 'io').read_text().splitlines())},
        'io_full': pressure_total('io'),
        'memory_full': pressure_total('memory'),
        'outputs': metrics['output'],
        'inputs': metrics['input'],
    }


def total(frame, group, key):
    return sum(value.get(key, 0) for value in frame[group].values())


def compare(before, after):
    if before['pid'] != after['pid']:
        raise RuntimeError('Agent restarted during the sample; do not continue rollout')
    seconds = after['time'] - before['time']
    return {
        'seconds': round(seconds, 1),
        'io_full_percent': round((after['io_full'] - before['io_full']) / seconds / 10000, 2),
        'memory_full_percent': round((after['memory_full'] - before['memory_full']) / seconds / 10000, 2),
        'agent_cpu_percent': round((after['cpu'] - before['cpu']) / seconds * 100, 2),
        'agent_read_KiB_s': round((after['io']['read_bytes'] - before['io']['read_bytes']) / seconds / 1024, 2),
        'agent_write_KiB_s': round((after['io']['write_bytes'] - before['io']['write_bytes']) / seconds / 1024, 2),
        'collected_records': total(after, 'inputs', 'records') - total(before, 'inputs', 'records'),
        'sent_records': total(after, 'outputs', 'proc_records') - total(before, 'outputs', 'proc_records'),
        'new_retries': total(after, 'outputs', 'retries') - total(before, 'outputs', 'retries'),
        'new_drops': total(after, 'outputs', 'dropped_records') - total(before, 'outputs', 'dropped_records'),
        'new_errors': total(after, 'outputs', 'errors') - total(before, 'outputs', 'errors'),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 300:
        parser.error('--seconds must be between 1 and 300')
    before = snapshot()
    time.sleep(args.seconds)
    print(json.dumps(compare(before, snapshot())))


if __name__ == '__main__':
    main()
