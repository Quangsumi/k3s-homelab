"""Offline fixtures for preserving existing networking while changing DNS."""
from copy import deepcopy
from pathlib import Path
import ipaddress
import unittest

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
ENV = Environment(undefined=StrictUndefined)
ENV.filters['bool'] = bool


def combine(original, update, recursive=False):
    """Fixture equivalent of recursive mapping merge, replacing lists."""
    result = deepcopy(original)
    for key, value in update.items():
        if recursive and isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = combine(result[key], value, recursive=True)
        else:
            result[key] = deepcopy(value)
    return result


ENV.filters['combine'] = combine
PLAY = yaml.safe_load((ROOT / 'playbooks/network.yml').read_text(encoding='utf-8-sig'))[0]
TASKS = PLAY['tasks']
CONDITIONS = TASKS[0]['ansible.builtin.assert']['that']
MERGE = next(t['ansible.builtin.set_fact']['network_desired'] for t in TASKS
             if 'network_desired' in t.get('ansible.builtin.set_fact', {}))
MATCH = next(t['when'] for t in TASKS if t['name'].startswith('Match the interface'))


def settings():
    return dict(ansible_host='tombstone.lab', network_address='192.168.63.20',
                network_manage=True, ansible_distribution='Ubuntu',
                ansible_service_mgr='systemd', network_interface='ens18',
                network_gateway='192.168.63.1', network_dns=['192.168.63.102'],
                network_rollback_seconds=180,
                ansible_default_ipv4=dict(address='192.168.63.20', interface='ens18',
                                          gateway='192.168.63.1', macaddress='bc:24:11:bd:1f:6a'))


def accepted(values):
    return all(ENV.compile_expression(c)(**values) for c in CONDITIONS)


def candidate(current, **overrides):
    values = settings()
    values.update(overrides)
    return ENV.compile_expression(MERGE.strip()[2:-2])(
        network_current=current, network_ids=['eth0'], **values)


class NetworkAddressTests(unittest.TestCase):
    def test_expected_address_accepted_independent_of_ssh_dns(self):
        self.assertTrue(accepted(settings()))

    def test_unexpected_address_or_os_rejected(self):
        for value in ['tombstone.lab', '192.168.63.99', None]:
            values = settings()
            values['network_address'] = value
            self.assertFalse(accepted(values))
        values = settings()
        del values['network_address']
        self.assertFalse(accepted(values))
        values = settings()
        values['ansible_distribution'] = 'Debian'
        self.assertFalse(accepted(values))

    def test_dns_merge_preserves_routes_ipv6_mac_search_and_other_interfaces(self):
        current = {'network': {'version': 2, 'renderer': 'networkd', 'ethernets': {
            'eth0': {'match': {'macaddress': 'bc:24:11:bd:1f:6a'}, 'set-name': 'ens18',
                     'addresses': ['192.168.63.20/24', 'fd00::20/64'], 'mtu': 1400,
                     'dhcp4': False, 'dhcp6': True,
                     'routes': [{'to': 'default', 'via': '192.168.63.1', 'metric': 100}],
                     'nameservers': {'addresses': ['192.168.63.1'], 'search': ['lab']}},
            'ens19': {'dhcp4': True}}}}
        expected = deepcopy(current)
        expected['network']['ethernets']['eth0']['nameservers']['addresses'] = ['192.168.63.102']
        self.assertEqual(candidate(current), expected)
        self.assertEqual(candidate(current, ansible_host='192.168.63.20'), expected)
        self.assertEqual(current['network']['ethernets']['eth0']['nameservers']['addresses'], ['192.168.63.1'])

    def test_mac_based_definition_can_match_without_interface_identifier(self):
        values = settings()
        self.assertTrue(ENV.compile_expression(MATCH)(item={
            'key': 'eth0', 'value': {'match': {'macaddress': 'BC:24:11:BD:1F:6A'}}}, **values))
        self.assertTrue(ENV.compile_expression(MATCH)(item={
            'key': 'eth0', 'value': {'set-name': 'ens18'}}, **values))
        self.assertFalse(ENV.compile_expression(MATCH)(item={
            'key': 'ens19', 'value': {}}, **values))

    def test_inventory_records_numeric_guest_addresses(self):
        inventory = yaml.safe_load((ROOT / 'inventory/hosts.yml').read_text(encoding='utf-8-sig'))
        groups = inventory['all']['children']['linux_vms']['children']
        for group in groups.values():
            for name, values in group['hosts'].items():
                with self.subTest(host=name):
                    self.assertEqual(ipaddress.ip_address(values['network_address']).version, 4)


if __name__ == '__main__':
    unittest.main()
