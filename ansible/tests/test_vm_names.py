"""Offline checks for the VM-ID-based Proxmox playbook. No VM access."""
import json
from pathlib import Path
import unittest
import yaml
from jinja2 import Environment, StrictUndefined, UndefinedError

ROOT = Path(__file__).resolve().parents[1]
ENV = Environment(undefined=StrictUndefined)
ENV.filters['from_json'] = json.loads
PLAY = yaml.safe_load((ROOT / 'playbooks/proxmox-agent.yml').read_text(encoding='utf-8-sig'))[0]


def evaluate(expression, **values):
    expression = expression.strip()
    if expression.startswith('{{'):
        expression = expression[2:-2].strip()
    return ENV.compile_expression(expression)(**values)


class VmIdTests(unittest.TestCase):
    def test_inventory_matches_the_supplied_screenshot(self):
        groups = yaml.safe_load((ROOT / 'inventory/hosts.yml').read_text())['all']['children']['linux_vms']['children']
        actual = {name: (v['vmid'], v['proxmox_name']) for g in groups.values() for name, v in g['hosts'].items()}
        expected = {'tombstone': 100, 'whyachi': 101, 'huge': 104, 'minotaur': 106,
                    'hydra': 108, 'valkyrie': 109, 'biteforce': 111}
        self.assertEqual(actual, {name: (vmid, name) for name, vmid in expected.items()})

    def test_lookup_follows_current_node_by_id(self):
        for node in ['endgame', 'deepsix']:
            records = [{'type': 'qemu', 'vmid': 109, 'node': node, 'name': 'valkyrie'},
                       {'type': 'qemu', 'vmid': 999, 'node': 'other', 'name': 'valkyrie'}]
            result = evaluate(PLAY['vars']['vm'], cluster_vms={'stdout': json.dumps(records)},
                              inventory_hostname='valkyrie', hostvars={'valkyrie': {'vmid': 109}})
            self.assertEqual(result['node'], node)
            self.assertEqual(result['vmid'], 109)

    def test_missing_vm_id_fails_before_config_mutation(self):
        result = evaluate(PLAY['vars']['vm'], cluster_vms={'stdout': '[]'},
                          inventory_hostname='valkyrie', hostvars={'valkyrie': {'vmid': 109}})
        with self.assertRaises(UndefinedError):
            ENV.from_string('{{ vm.node }}').render(vm=result)

    def test_identity_locks_templates_and_custom_options_are_checked(self):
        conditions = PLAY['tasks'][2]['ansible.builtin.assert']['that']
        def accepted(config):
            return all(evaluate(c, config=config, proxmox_name='valkyrie') for c in conditions)
        self.assertTrue(accepted({'name': 'valkyrie', 'agent': '0'}))
        for bad in [{'name': 'other'}, {'name': 'valkyrie', 'lock': 'migrate'},
                    {'name': 'valkyrie', 'template': 1},
                    {'name': 'valkyrie', 'agent': 'enabled=1,type=virtio'}]:
            self.assertFalse(accepted(bad))
        self.assertIn('--digest', PLAY['tasks'][3]['ansible.builtin.command'])

    def test_enabled_vms_are_skipped_and_no_helper_is_needed(self):
        condition = PLAY['tasks'][3]['when']
        for value, change in [('0', True), ('enabled=0', True), ('1', False), ('enabled=1', False)]:
            self.assertEqual(evaluate(condition, config={'agent': value}), change)
        self.assertEqual(len(PLAY['tasks']), 4)
        self.assertFalse((ROOT / 'playbooks/tasks/find-proxmox-vm.yml').exists())


if __name__ == '__main__':
    unittest.main()
