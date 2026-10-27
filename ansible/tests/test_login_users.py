"""Offline tests of login defaults and privilege boundaries; no VM access."""

from pathlib import Path
import re
import unittest

import yaml
from jinja2 import Environment, StrictUndefined


ROOT = Path(__file__).resolve().parents[1]
ENV = Environment(undefined=StrictUndefined)
ENV.tests['match'] = lambda value, pattern: re.match(pattern, value) is not None
ENV.filters['bool'] = bool  # Policy-render fixtures below pass actual Python booleans.


def load(path):
    return yaml.safe_load((ROOT / path).read_text(encoding='utf-8-sig'))


def evaluate(expression, **values):
    expression = expression.strip()
    if expression.startswith('{{'):
        expression = expression[2:-2].strip()
    return ENV.compile_expression(expression)(**values)


class UserLoginTests(unittest.TestCase):
    def test_vm_username_follows_vm_alias(self):
        settings = load('inventory/group_vars/linux_vms.yml')
        for name in ['valkyrie', 'huge', 'tombstone']:
            self.assertEqual(evaluate(settings['ansible_user'], inventory_hostname=name), name)
        self.assertEqual(load('inventory/group_vars/proxmox_hosts.yml')['ansible_user'], 'root')

    def test_key_jobs_edit_only_the_login_users_keys_without_sudo(self):
        for path in ['playbooks/ssh-keys/beginner/main.yml', 'playbooks/ssh-keys/main.yml']:
            play = load(path)[0]
            self.assertFalse(play['become'])
            module = play['tasks'][0]['ansible.posix.authorized_key']
            self.assertEqual(evaluate(module['user'], ansible_user='valkyrie'), 'valkyrie')
            self.assertFalse(module['exclusive'])

    def test_sudo_password_available_with_key_authentication(self):
        expression = load('inventory/group_vars/linux_vms.yml')['ansible_become_password']
        vault = {'valkyrie': {'ssh_password': 'example-login', 'sudo_password': 'example-sudo'}}
        self.assertEqual(evaluate(expression, inventory_hostname='valkyrie', vault_hosts=vault,
                                  bootstrap_password_auth=False), 'example-sudo')
        self.assertIsNone(evaluate(expression, inventory_hostname='valkyrie'))

    def test_baseline_and_network_use_sudo_only_for_nonroot(self):
        for path in ['playbooks/baseline/main.yml', 'playbooks/network/main.yml']:
            expression = load(path)[0]['become']
            self.assertTrue(evaluate(expression, ansible_user='valkyrie'))
            self.assertFalse(evaluate(expression, ansible_user='root'))

    def test_biteforce_uses_key_auth_even_during_password_bootstrap(self):
        settings = load('inventory/host_vars/biteforce.yml')
        self.assertEqual(settings['ansible_user'], 'biteforce')
        self.assertEqual(settings['ansible_ssh_private_key_file'], '~/.ssh/homelab_laptop')
        self.assertIn('ansible_password', settings)
        self.assertIsNone(settings['ansible_password'])
        self.assertNotIn('ssh_password_login', settings)
        self.assertNotIn('ansible_ssh_common_args', settings)
        shared = load('inventory/group_vars/all/main.yml')
        # Model inventory precedence: the host's null replaces the shared expression.
        merged = {**shared, **settings, 'bootstrap_password_auth': True}
        self.assertIsNone(merged['ansible_password'])
        expression = shared['ansible_password']
        self.assertEqual(evaluate(expression, bootstrap_password_auth=True,
                                  inventory_hostname='hydra',
                                  vault_hosts={'hydra': {'ssh_password': 'example-root'}}), 'example-root')

    def test_hydra_uses_root_and_is_excluded_from_generic_admin_jobs(self):
        settings = load('inventory/host_vars/hydra.yml')
        self.assertEqual(settings['ansible_user'], 'root')
        self.assertFalse(settings['network_manage'])
        children = load('inventory/hosts.yml')['all']['children']['linux_vms']['children']
        self.assertEqual(set(children['nas_appliances']['hosts']), {'hydra'})
        for path in ['playbooks/baseline/main.yml', 'playbooks/root-access/main.yml', 'playbooks/network/main.yml']:
            self.assertEqual(load(path)[0]['hosts'], 'linux_vms:!nas_appliances')
        self.assertIn('linux_vms', load('playbooks/ssh-keys/main.yml')[0]['hosts'].split(':'))

    def test_root_password_requires_a_real_hash_and_suppresses_logging(self):
        play = load('playbooks/root-access/main.yml')[0]
        task = next(t for t in play['tasks'] if t['name'].startswith('Require a real root password'))
        self.assertTrue(task['no_log'])
        expression = task['ansible.builtin.assert']['that'][0]
        for value, expected in [('REPLACE_WITH_HASH', False), ('password06', False),
                                ('$6$salt$' + 'A' * 86, True)]:
            self.assertEqual(evaluate(expression, vault_hosts={'valkyrie': {'root_password_hash': value}},
                                      inventory_hostname='valkyrie'), expected)
        password_task = next(t for t in play['tasks'] if 'ansible.builtin.user' in t)
        self.assertTrue(password_task['no_log'])
        self.assertFalse(password_task['ansible.builtin.user']['password_lock'])

    def test_root_policy_is_scoped_to_root_and_can_disable_password_ssh(self):
        play = load('playbooks/root-access/main.yml')[0]
        block = next(t['block'] for t in play['tasks'] if 'block' in t)
        policy = block[0]['ansible.builtin.blockinfile']
        self.assertIn('sshd -t', policy['validate'])
        for enabled, password_line in [(True, 'PasswordAuthentication yes'), (False, 'PasswordAuthentication no')]:
            result = ENV.from_string(policy['block']).render(root_ssh_password_login=enabled)
            self.assertTrue(result.startswith('Match User root\n'))
            self.assertIn(password_line, result)
            self.assertTrue(result.rstrip().endswith('Match all'))


if __name__ == '__main__':
    unittest.main()
