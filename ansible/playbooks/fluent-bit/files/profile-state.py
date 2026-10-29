"""Inspect unused bookmarks, or explicitly reset them. Never change queue files."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


SUFFIXES = ('', '-wal', '-shm', '-journal')


def running_paths():
    """Use open files, not just the configuration left on disk after a failed restart."""
    result = subprocess.run(
        ['systemctl', 'show', 'fluent-bit', '-p', 'MainPID', '-p', 'LoadState'],
        capture_output=True, text=True, timeout=5
    )
    status = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if status.get('LoadState') == 'not-found':
        return set()  # A first installation has no active agent/bookmark files.
    if result.returncode or 'MainPID' not in status:
        raise RuntimeError('Cannot inspect the agent service; no bookmarks were deleted')
    pid = status['MainPID']
    if not pid or pid == '0':
        return set()
    paths = set()
    try:
        for descriptor in (Path('/proc') / pid / 'fd').iterdir():
            try:
                paths.add(str(descriptor.readlink()))
            except FileNotFoundError:
                pass  # A descriptor closed while the agent was running.
    except FileNotFoundError:
        pass  # The old process exited; reset checks again before deleting files.
    return paths


def inspect_state(directory, names, config, save_positions, disk_buffering, runtime_paths=None, queue_limit=None):
    directory = directory.resolve()
    active_databases = set()
    active_queue = None
    if config.exists():
        for line in config.read_text().splitlines():
            fields = line.strip().split(None, 1)
            if len(fields) != 2 or fields[0].startswith('#'):
                continue
            if fields[0].lower() == 'db':
                active_databases.add(str(Path(fields[1].strip()).resolve()))
            elif fields[0].lower() == 'storage.path':
                active_queue = str(Path(fields[1].strip()).resolve())
    queue = directory / 'queue'
    if runtime_paths is not None:
        active_databases = runtime_paths
        if any(path.startswith(str(queue) + '/') for path in runtime_paths):
            active_queue = str(queue)
        elif not any(str(directory / (name + '.db' + suffix)) in runtime_paths
                     for name in names for suffix in SUFFIXES):
            active_queue = None
    parked = [name for name in names if not any(str(directory / (name + '.db' + suffix))
                                               in active_databases for suffix in SUFFIXES)
              and any((directory / (name + '.db' + suffix)).exists() for suffix in SUFFIXES)]
    queue_bytes = 0
    has_queue = False
    if disk_buffering and queue.exists():
        for path in queue.rglob('*'):
            try:
                if path.is_file():
                    has_queue = True
                    queue_bytes += path.stat().st_size
            except FileNotFoundError:
                pass  # The active agent sent and removed this chunk during inspection.
    limit_bytes = int(queue_limit[:-1]) * 1024 * 1024 if queue_limit else None
    resume_queue = bool(disk_buffering and has_queue and active_queue != str(queue))
    return {
        'unused_bookmarks': parked if save_positions else [],
        'resume_queued_logs': resume_queue,
        'needs_choice': bool((save_positions and parked) or resume_queue),
        'queue_bytes': queue_bytes,
        'queue_limit_bytes': limit_bytes,
        # File sizes include overhead. Stop conservatively rather than risk silent eviction.
        'queue_would_overflow': bool(disk_buffering and limit_bytes is not None and queue_bytes > limit_bytes),
    }


def reset_bookmarks(directory, names, config, runtime_paths=None):
    directory = directory.resolve()
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in names):
        raise RuntimeError('Invalid bookmark name; no files deleted')
    state = inspect_state(directory, names, config, True, False, runtime_paths)
    if not state['unused_bookmarks']:
        raise RuntimeError('No unused bookmarks to reset; active bookmarks are never deleted')
    candidates = [directory / (name + '.db' + suffix) for name in state['unused_bookmarks']
                  for suffix in SUFFIXES]
    # Reject broken links too, before deleting any member of a database family.
    if any(path.is_symlink() for path in candidates):
        raise RuntimeError('Expected regular unused bookmark files; no files deleted')
    files = [path for path in candidates if path.exists()]
    if any(not path.is_file() for path in files):
        raise RuntimeError('Expected regular unused bookmark files; no files deleted')
    for path in files:
        path.unlink()
    return {'removed_bookmark_files': [path.name for path in files], 'queue': 'untouched'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['inspect', 'reset'])
    args = parser.parse_args()
    settings = json.load(sys.stdin)
    directory = Path(settings['directory'])
    names = ['journal'] + settings['extra_names']
    config = Path('/etc/fluent-bit/fluent-bit.conf')
    if config.is_symlink() or directory.is_symlink():
        raise RuntimeError('Review symbolic links before handling profile state')
    if args.action == 'inspect':
        result = inspect_state(directory, names, config, settings['save_positions'],
                               settings['disk_buffering'], running_paths(), settings['queue_limit'])
    else:
        result = reset_bookmarks(directory, names, config, runtime_paths=running_paths())
    print(json.dumps(result))


if __name__ == '__main__':
    main()
