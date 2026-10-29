"""Local profile/isolation/state tests. Never contact live homelab machines."""

import copy
import http.server
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from ansible.plugins.filter.core import FilterModule
import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / 'playbooks/fluent-bit'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAMPLER = load_module('sample_load', PLAY / 'files/sample-load.py')
STATE = load_module('profile_state', PLAY / 'files/profile-state.py')


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.settings = yaml.safe_load((PLAY / 'settings.yml').read_text())
        self.settings.update({
            'fluent_bit_read_from_tail': True,
            'inventory_hostname': 'test-host', 'groups': {'proxmox_hosts': []},
            'fluent_bit_external_token': 'test-token',
            'fluent_bit_gateway_host': '127.0.0.1', 'fluent_bit_gateway_port': 31419,
            'fluent_bit_gateway_tls_name': 'otel-otlp.lab',
            'fluent_bit_extra_files': [{'name': 'demo', 'path': '/var/log/demo.log'}],
        })
        self.env = jinja2.Environment(undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
        self.env.filters['bool'] = FilterModule().filters()['bool']

    def values(self, profile):
        complete = dict(self.settings['fluent_bit_profiles'][profile])
        complete.update(self.settings['fluent_bit_profile_overrides'][profile])
        return dict(self.settings, fluent_bit_profile=profile, fluent_bit_settings=complete)

    def render(self, profile):
        return self.env.from_string((PLAY / 'templates/fluent-bit.conf.j2').read_text()).render(self.values(profile))

    @staticmethod
    def directives(config):
        return [line.strip().split(None, 1) for line in config.splitlines()
                if line.strip() and not line.lstrip().startswith(('#', '['))]

    def test_all_profiles_are_complete_and_match_documentation(self):
        rows = {}
        for line in (PLAY / 'PROFILES.md').read_text().splitlines():
            if line.startswith('| `'):
                columns = [c.strip() for c in line.strip('|').split('|')]
                rows[columns[0].strip('`')] = [c.split(' (unused)')[0] for c in columns[1:]]
        profiles = self.settings['fluent_bit_profiles']
        self.assertEqual(list(profiles), ['survival', 'light', 'buffered', 'busy'])
        self.assertEqual(self.settings['fluent_bit_profile'], 'survival')
        for index, (name, settings) in enumerate(profiles.items()):
            self.assertEqual(set(settings), set(rows), name)
            for key, value in settings.items():
                expected = str(value).lower() if isinstance(value, bool) else str(value)
                self.assertEqual(rows[key][index], expected, (name, key))

    def test_all_profiles_render_their_own_values_in_the_shared_host_folder(self):
        for name, settings in self.settings['fluent_bit_profiles'].items():
            with self.subTest(profile=name):
                directives = self.directives(self.render(name))
                databases = [v for k, v in directives if k == 'DB']
                queues = [v for k, v in directives if k == 'storage.path']
                self.assertEqual(len(databases), 2 if settings['save_positions'] else 0)
                self.assertEqual(len(queues), 1 if settings['disk_buffering'] else 0)
                self.assertEqual(databases, ['/var/lib/fluent-bit/host/journal.db', '/var/lib/fluent-bit/host/demo.db']
                                 if settings['save_positions'] else [])
                self.assertEqual(queues, ['/var/lib/fluent-bit/host/queue'] if settings['disk_buffering'] else [])
                self.assertNotIn(['DB.Sync', 'Full'], directives)
                self.assertNotIn(['storage.sync', 'full'], directives)
                self.assertIn(['Rate_Gate.Max_Records', str(settings['rate_records'])], directives)
                self.assertIn(['Rate_Gate.Max_Bytes', settings['rate_bytes']], directives)
                if settings['disk_buffering']:
                    self.assertIn(['storage.total_limit_size', settings['queue_limit']], directives)
                    self.assertFalse(any(k == 'Mem_Buf_Limit' for k, _ in directives))
                else:
                    self.assertIn(['Mem_Buf_Limit', settings['memory_buffer']], directives)
                self.assertIn(['Header', 'Authorization Bearer test-token'], directives)

    def test_switching_to_survival_does_not_inherit_busy_settings_or_overrides(self):
        self.settings['fluent_bit_profile_overrides']['busy'] = {'cpu_quota_percent': 7}
        unit = self.env.from_string((PLAY / 'templates/20-host-logs-limits.conf.j2').read_text())
        self.assertIn('CPUQuota=7%', unit.render(self.values('busy')))
        self.render('busy')
        survival = self.directives(self.render('survival'))
        self.assertIn('CPUQuota=5%', unit.render(self.values('survival')))
        self.assertIn(['Rate_Gate.Max_Records', '20'], survival)
        self.assertFalse(any(k in ['DB', 'storage.path', 'storage.total_limit_size'] for k, _ in survival))
        self.render('buffered')
        self.assertFalse(any(k == 'DB' for k, _ in self.directives(self.render('light'))))

    def test_agent_diagnostics_do_not_filter_source_log_levels(self):
        error = self.directives(self.render('light'))
        self.settings['fluent_bit_profile_overrides']['light'] = {'agent_diagnostic_log_level': 'info'}
        info = self.directives(self.render('light'))
        self.assertIn(['Log_Level', 'error'], error)
        self.assertIn(['Log_Level', 'info'], info)
        self.assertEqual([pair for pair in error if pair[0] != 'Log_Level'],
                         [pair for pair in info if pair[0] != 'Log_Level'])

    def run_assertions(self, tasks, extra):
        runner = str(Path(sys.executable).with_name('ansible-playbook'))
        play = [{'hosts': 'all', 'connection': 'local', 'gather_facts': False,
                 'vars_files': [str(PLAY / 'settings.yml')],
                 'vars': {'fluent_bit_extra_files': [], 'fluent_bit_read_from_tail': True},
                 'tasks': tasks}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'assertions.yml'
            path.write_text(yaml.safe_dump(play, sort_keys=False))
            return subprocess.run([runner, '-i', 'localhost,', '--limit', 'all', str(path),
                                   '--extra-vars', json.dumps(extra)],
                                  capture_output=True, text=True, timeout=25)

    def test_native_ansible_accepts_profiles_and_rejects_invalid_collections(self):
        tasks = [{'ansible.builtin.import_tasks': str(PLAY / 'tasks/validate-settings.yml')}]
        cases = [({'fluent_bit_profile': name}, True) for name in self.settings['fluent_bit_profiles']]
        cases += [({'fluent_bit_profile': 'unknown'}, False),
                  ({'fluent_bit_cpu_quota_percent': 25}, False),
                  ({'fluent_bit_state_directory': '/var/lib/fluent-bit/host/permanent'}, False)]
        for level in ['warn', 'info']:
            overrides = copy.deepcopy(self.settings['fluent_bit_profile_overrides'])
            overrides['light'] = {'agent_diagnostic_log_level': level}
            cases.append(({'fluent_bit_profile': 'light', 'fluent_bit_profile_overrides': overrides}, True))
        for changes in [{'cpu_quota_percent': True}, {'cpu_quota_percent': 25},
                        {'rate_records': 1000}, {'disk_buffering': True}, {'rate_record': 80}, {'log_level': 'info'}]:
            overrides = copy.deepcopy(self.settings['fluent_bit_profile_overrides'])
            overrides['survival'] = changes
            cases.append(({'fluent_bit_profile_overrides': overrides}, False))
        incomplete = copy.deepcopy(self.settings['fluent_bit_profiles'])
        del incomplete['busy']['memory_buffer']
        cases.append(({'fluent_bit_profiles': incomplete}, False))
        cases.append(({'fluent_bit_settings': self.settings['fluent_bit_profiles']['busy']}, False))
        for extra, allowed in cases:
            with self.subTest(extra=extra):
                result = self.run_assertions(tasks, extra)
                self.assertEqual(result.returncode == 0, allowed, result.stdout[-1500:] + result.stderr[-500:])

    def test_native_ansible_reselects_fresh_settings_in_one_run(self):
        overrides = copy.deepcopy(self.settings['fluent_bit_profile_overrides'])
        overrides['busy'] = {'cpu_quota_percent': 7}
        tasks = [
            {'ansible.builtin.set_fact': {'fluent_bit_profile': 'busy'}},
            {'ansible.builtin.assert': {'that': 'fluent_bit_settings.cpu_quota_percent == 7'}},
            {'ansible.builtin.set_fact': {'fluent_bit_profile': 'survival'}},
            {'ansible.builtin.assert': {'that': [
                'fluent_bit_settings.cpu_quota_percent == 5',
                'fluent_bit_settings.rate_records == 20',
                'not fluent_bit_settings.disk_buffering', 'not fluent_bit_settings.save_positions']}},
        ]
        result = self.run_assertions(tasks, {'fluent_bit_profile_overrides': overrides})
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-500:])

    def test_native_ansible_requires_an_explicit_state_choice(self):
        tasks = yaml.safe_load((PLAY / 'tasks/profile-state.yml').read_text())
        gate = next(t for t in tasks if t['name'].startswith('Stop unless'))
        for choice, bookmarks, allowed in [('resume', ['journal'], True), ('new', ['journal'], True),
                                           ('ask', ['journal'], False), ('new', [], False), ('resume', [], True)]:
            with self.subTest(choice=choice, bookmarks=bookmarks):
                result = self.run_assertions([gate], {
                    'fluent_bit_state_choice': choice,
                    'fluent_bit_existing_state': {'needs_choice': True, 'unused_bookmarks': bookmarks}})
                self.assertEqual(result.returncode == 0, allowed, result.stdout[-1500:] + result.stderr[-500:])

    def test_native_ansible_blocks_queue_cap_that_could_drop_waiting_logs(self):
        tasks = yaml.safe_load((PLAY / 'tasks/profile-state.yml').read_text())
        gate = next(t for t in tasks if t['name'].startswith('Stop before a smaller queue limit'))
        for oversized in [False, True]:
            result = self.run_assertions([gate], {'fluent_bit_existing_state': {
                'queue_would_overflow': oversized, 'queue_bytes': 70 * 1024 * 1024,
                'queue_limit_bytes': 64 * 1024 * 1024}})
            self.assertEqual(result.returncode == 0, not oversized, result.stdout[-1500:] + result.stderr[-500:])

    def test_single_playbook_and_no_retired_survival_paths(self):
        play = yaml.safe_load((PLAY / 'main.yml').read_text())[0]
        self.assertEqual(play['serial'], 1)
        self.assertTrue(play['any_errors_fatal'])
        install = next(t for t in play['tasks'] if t.get('ansible.builtin.include_tasks') == 'tasks/install.yml')
        self.assertEqual(install['when'], 'fluent_bit_install_package | bool')
        for name in ['emergency.yml', 'rollout.yml', 'ROLLOUT.md', 'files/apply-survival-profile.py']:
            self.assertFalse((PLAY / name).exists())

    def test_actual_fluent_bit_accepts_all_profiles(self):
        binary = os.environ.get('FLUENT_BIT_TEST_BINARY')
        if not binary:
            self.skipTest('Set FLUENT_BIT_TEST_BINARY to test with the actual installed binary')
        ca = ROOT.parent / 'pki/bundles/application-trust.pem'
        for name in self.settings['fluent_bit_profiles']:
            with self.subTest(profile=name), tempfile.TemporaryDirectory() as directory:
                config = self.render(name).replace('/var/lib/fluent-bit/host', directory)
                config = config.replace('/etc/fluent-bit/gateway-ca.pem', str(ca))
                path = Path(directory) / 'agent.conf'
                path.write_text(config)
                result = subprocess.run([binary, '--dry-run', '--config=' + str(path)],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr[-1800:])

    def test_queue_and_read_position_survive_local_outage_and_restart(self):
        binary = os.environ.get('FLUENT_BIT_TEST_BINARY')
        if not binary:
            self.skipTest('Set FLUENT_BIT_TEST_BINARY for the local outage/restart test')
        state = {'available': False, 'attempts': 0, 'received': []}

        class Receiver(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                state['attempts'] += 1
                if state['available']:
                    state['received'].append(body)
                self.send_response(200 if state['available'] else 503)
                self.send_header('Content-Length', '0')
                self.end_headers()

            def log_message(self, *_):
                pass

        def wait_until(predicate):
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(0.1)
            self.fail('Local Fluent Bit outage/restart test timed out')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.log'
            source.write_text('')
            receiver = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
            thread = threading.Thread(target=receiver.serve_forever, daemon=True)
            thread.start()
            config = self.render('buffered')
            # Synthetic tail fixture only. Never read the controller's real journal.
            blocks = re.split(r'(?=^\[)', config, flags=re.M)
            config = ''.join(block for block in blocks if not
                             (block.startswith('[INPUT]') and 'Name              systemd' in block))
            config = config.replace('/var/lib/fluent-bit/host', directory)
            config = config.replace('/var/log/demo.log', str(source))
            config = config.replace('Port                      31419', 'Port                      ' + str(receiver.server_port))
            config = config.replace('TLS                       On', 'TLS                       Off')
            config = config.replace('Flush                     10', 'Flush                     1')
            config = config.replace('Grace                     30', 'Grace                     1')
            config = config.replace('Refresh_Interval  5', 'Refresh_Interval  1')
            path = root / 'agent.conf'
            path.write_text(config)
            process = None
            with (root / 'agent-errors.log').open('w+') as errors:
                try:
                    process = subprocess.Popen([binary, '--config=' + str(path)],
                                               stdout=subprocess.DEVNULL, stderr=errors)
                    wait_until(lambda: (root / 'demo.db').exists())
                    time.sleep(0.5)
                    marker = 'local-only-permanent-queue-test'
                    source.write_text(marker + '\n')
                    wait_until(lambda: state['attempts'] > 0)
                    self.assertEqual(state['received'], [])
                    process.terminate()
                    process.wait(timeout=10)
                    with sqlite3.connect(root / 'demo.db') as db:
                        self.assertEqual(db.execute('SELECT offset FROM in_tail_files').fetchone()[0], source.stat().st_size)
                    state['available'] = True
                    process = subprocess.Popen([binary, '--config=' + str(path)],
                                               stdout=subprocess.DEVNULL, stderr=errors)
                    wait_until(lambda: any(marker.encode() in body for body in state['received']))
                finally:
                    if process is not None and process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    receiver.shutdown()
                    receiver.server_close()


class StateChoiceTests(unittest.TestCase):
    def test_existing_queue_is_measured_before_applying_a_smaller_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / 'queue/systemd.0'
            queue.mkdir(parents=True)
            chunk = queue / 'existing.flb'
            with chunk.open('wb') as stream:
                stream.truncate(70 * 1024 * 1024)  # Sparse fixture: metadata, not 70 MB of writes.
            config = root / 'missing.conf'
            info = STATE.inspect_state(root, ['journal'], config, True, True, queue_limit='64M')
            self.assertTrue(info['queue_would_overflow'])
            self.assertTrue(info['needs_choice'])
            self.assertFalse(STATE.inspect_state(root, ['journal'], config, True, True,
                                                queue_limit='128M')['queue_would_overflow'])
            self.assertFalse(STATE.inspect_state(root, ['journal'], config, False, False,
                                                queue_limit='64M')['queue_would_overflow'])
            self.assertEqual(chunk.stat().st_size, 70 * 1024 * 1024)

    def test_missing_service_is_fresh_but_an_inspection_error_stops(self):
        missing = subprocess.CompletedProcess([], 4, 'LoadState=not-found\nMainPID=0\n', '')
        with mock.patch.object(STATE.subprocess, 'run', return_value=missing):
            self.assertEqual(STATE.running_paths(), set())
        failed = subprocess.CompletedProcess([], 1, '', 'Service manager unavailable')
        with mock.patch.object(STATE.subprocess, 'run', return_value=failed):
            with self.assertRaisesRegex(RuntimeError, 'Cannot inspect'):
                STATE.running_paths()

    def test_runtime_bookmarks_win_over_stale_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            db = state / 'journal.db'
            db.write_text('saved position')
            config = state / 'agent.conf'
            config.write_text('[INPUT]\n DB ' + str(db) + '\n')
            # Disk config was written, but the running agent still uses RAM.
            self.assertTrue(STATE.inspect_state(state, ['journal'], config, True, True, set())['needs_choice'])
            config.write_text('[INPUT]\n Name systemd\n')
            # A RAM config was written, but the old process still holds its database.
            self.assertFalse(STATE.inspect_state(state, ['journal'], config, True, False, {str(db)})['needs_choice'])
            with self.assertRaisesRegex(RuntimeError, 'No unused bookmarks'):
                STATE.reset_bookmarks(state, ['journal'], config, {str(db)})
            self.assertEqual(db.read_text(), 'saved position')

    def test_new_deletes_only_unused_bookmarks_without_creating_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'normal'
            state.mkdir()
            db = state / 'journal.db'
            db.write_text('bookmark: line 100')
            (state / 'journal.db-wal').write_text('saved transaction')
            (state / 'journal.db-shm').write_text('shared metadata')
            (state / 'journal.db-journal').write_text('rollback metadata')
            (state / 'other.db').write_text('not a configured bookmark')
            queue = state / 'queue/systemd.0'
            queue.mkdir(parents=True)
            chunk = queue / 'pending.flb'
            chunk.write_text('unsent log before line 100')
            (queue / 'journal.db').write_text('queue file with a similar name')
            config = root / 'agent.conf'
            config.write_text('[INPUT]\n    Name systemd\n    storage.type memory\n')
            info = STATE.inspect_state(state, ['journal'], config, True, True)
            self.assertTrue(info['needs_choice'])
            self.assertTrue(info['resume_queued_logs'])
            self.assertEqual(info['unused_bookmarks'], ['journal'])
            # RESUME is read-only: the saved line 100 remains available, with its replay tradeoff.
            self.assertEqual(db.read_text(), 'bookmark: line 100')
            reset = STATE.reset_bookmarks(state, ['journal'], config)
            self.assertFalse(db.exists())
            self.assertEqual(reset['queue'], 'untouched')
            self.assertFalse((state / 'journal.db-wal').exists())
            self.assertFalse((state / 'journal.db-shm').exists())
            self.assertFalse((state / 'journal.db-journal').exists())
            self.assertFalse((root / 'backups').exists())
            self.assertEqual(chunk.read_text(), 'unsent log before line 100')
            self.assertEqual((queue / 'journal.db').read_text(), 'queue file with a similar name')
            self.assertEqual((state / 'other.db').read_text(), 'not a configured bookmark')
            self.assertEqual(set(reset['removed_bookmark_files']),
                             {'journal.db', 'journal.db-wal', 'journal.db-shm', 'journal.db-journal'})
            self.assertEqual({p.name for p in state.iterdir()}, {'other.db', 'queue'})

    def test_new_rejects_escaping_names_and_linked_sidecars_before_deleting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / 'journal.db'
            db.write_text('saved position')
            config = root / 'missing.conf'
            with self.assertRaisesRegex(RuntimeError, 'Invalid bookmark name'):
                STATE.reset_bookmarks(root, ['../journal'], config)
            (root / 'journal.db-wal').symlink_to(root / 'missing-target')
            with self.assertRaisesRegex(RuntimeError, 'Expected regular'):
                STATE.reset_bookmarks(root, ['journal'], config)
            self.assertEqual(db.read_text(), 'saved position')

    def test_active_disk_state_is_reused_and_cannot_be_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / 'journal.db').write_text('active bookmark')
            config = state / 'agent.conf'
            config.write_text('[SERVICE]\n storage.path ' + str(state / 'queue') +
                              '\n[INPUT]\n DB ' + str(state / 'journal.db') + '\n')
            self.assertFalse(STATE.inspect_state(state, ['journal'], config, True, True)['needs_choice'])
            with self.assertRaisesRegex(RuntimeError, 'No unused bookmarks'):
                STATE.reset_bookmarks(state, ['journal'], config)
            self.assertEqual((state / 'journal.db').read_text(), 'active bookmark')

    def test_fresh_state_and_ram_profiles_need_no_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'missing.conf'
            self.assertFalse(STATE.inspect_state(root, ['journal'], config, True, True)['needs_choice'])
            (root / 'journal.db').write_text('parked bookmark')
            self.assertFalse(STATE.inspect_state(root, ['journal'], config, False, False)['needs_choice'])

class LoadSampleTests(unittest.TestCase):
    def frames(self):
        before = {'time': 100, 'pid': '123', 'cpu': 1, 'io_full': 1000,
                  'memory_full': 1000, 'io': {'read_bytes': 0, 'write_bytes': 0},
                  'inputs': {'journal': {'records': 10}},
                  'outputs': {'otlp': {'proc_records': 8, 'retries': 2,
                                       'dropped_records': 0, 'errors': 0}}}
        after = copy.deepcopy(before)
        after.update(time=160, cpu=4, io_full=1201000, memory_full=601000,
                     io={'read_bytes': 61440, 'write_bytes': 122880})
        after['inputs']['journal']['records'] += 100
        after['outputs']['otlp']['proc_records'] += 90
        after['outputs']['otlp']['retries'] += 1
        return before, after

    def test_pressure_cpu_and_delivery_deltas(self):
        before, after = self.frames()
        sample = SAMPLER.compare(before, after)
        self.assertEqual(sample['io_full_percent'], 2)
        self.assertEqual(sample['memory_full_percent'], 1)
        self.assertEqual(sample['agent_cpu_percent'], 5)
        self.assertEqual(sample['agent_read_KiB_s'], 1)
        self.assertEqual(sample['agent_write_KiB_s'], 2)
        self.assertEqual(sample['collected_records'], 100)
        self.assertEqual(sample['sent_records'], 90)
        self.assertEqual(sample['new_retries'], 1)

    def test_restart_during_observation_cannot_pass(self):
        before, after = self.frames()
        after['pid'] = '456'
        with self.assertRaisesRegex(RuntimeError, 'restarted'):
            SAMPLER.compare(before, after)


if __name__ == '__main__':
    unittest.main()
