"""Build real Kustomize resources locally. Never access a Kubernetes cluster."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[4]
APP = Path('apps/monitoring/fluent-bit')
KUBECTL = os.environ.get('KUBECTL', 'kubectl')


def build(root):
    result = subprocess.run(
        [KUBECTL, 'kustomize', str(root / APP)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    return list(yaml.safe_load_all(result.stdout))


def pod_and_maps(resources):
    daemonset = next(item for item in resources if item['kind'] == 'DaemonSet')
    maps = {item['metadata']['name']: item for item in resources if item['kind'] == 'ConfigMap'}
    return daemonset, maps


@unittest.skipUnless(shutil.which(KUBECTL), 'kubectl is required for local rendering')
class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources = build(ROOT)
        cls.daemonset, cls.maps = pod_and_maps(cls.resources)
        cls.pod = cls.daemonset['spec']['template']['spec']
        cls.container = cls.pod['containers'][0]
        cls.volumes = {volume['name']: volume for volume in cls.pod['volumes']}

    def test_every_profile_resolves_shared_settings_and_secret_without_plaintext_token(self):
        settings_name = self.container['envFrom'][0]['configMapRef']['name']
        settings = self.maps[settings_name]['data']
        profiles = self.maps[self.volumes['config']['configMap']['name']]['data']
        token_env = next(item for item in self.container['env']
                         if item['name'] == 'OTEL_GATEWAY_APP_BEARER_TOKEN')
        token_ref = token_env['valueFrom']['secretKeyRef']
        source = next(item for item in self.resources if item['kind'] == 'ExternalSecret')
        self.assertEqual(source['spec']['target']['name'], token_ref['name'])
        self.assertEqual(source['spec']['data'][0]['secretKey'], token_ref['key'])
        self.assertEqual(source['spec']['data'][0]['remoteRef']['key'], '/otel-gateway/APP_BEARER_TOKEN')
        self.assertNotIn('OTEL_GATEWAY_APP_BEARER_TOKEN', settings)
        self.assertFalse(any(item['kind'] == 'Secret' for item in self.resources))
        self.assertEqual(len(profiles), 4)
        for name, config in profiles.items():
            with self.subTest(profile=name):
                references = set(re.findall(r'\$\{([A-Z_]+)\}', config))
                self.assertEqual(references - settings.keys(), {'OTEL_GATEWAY_APP_BEARER_TOKEN'})
                output = config.split('[OUTPUT]')[1]
                self.assertIn('Logs_URI      ${OTEL_GATEWAY_POD_LOGS_URI}', output)
                self.assertEqual(settings['OTEL_GATEWAY_POD_LOGS_URI'], '/v1/logs')
                self.assertIn('Authorization Bearer ${OTEL_GATEWAY_APP_BEARER_TOKEN}', output)
                for directive in ['TLS', 'TLS.Verify', 'TLS.Verify_Hostname']:
                    self.assertRegex(output, rf'(?m)^\s*{re.escape(directive)}\s+On$')

    def test_ca_path_and_hashed_configmap_references_are_connected(self):
        settings = self.maps[self.container['envFrom'][0]['configMapRef']['name']]['data']
        ca = self.maps[self.volumes['gateway-ca']['configMap']['name']]
        mount = next(item for item in self.container['volumeMounts'] if item['name'] == 'gateway-ca')
        key = self.volumes['gateway-ca']['configMap']['items'][0]
        self.assertEqual(settings['OTEL_GATEWAY_CA_FILE'], mount['mountPath'] + '/' + key['path'])
        self.assertTrue(mount['readOnly'])
        self.assertEqual(ca['data'][key['key']], (ROOT / 'pki/public/tantrum-caddy.crt').read_text())
        self.assertTrue(all(item['immutable'] for item in self.maps.values()))
        self.assertTrue(all(item['metadata']['namespace'] == 'monitoring' for item in self.maps.values()))

    def test_destination_change_creates_new_settings_snapshot_without_changing_profiles_or_ca(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / APP, root / APP)
            shutil.copytree(ROOT / 'pki/public', root / 'pki/public')
            path = root / APP / 'gateway.env'
            path.write_text(path.read_text().replace('192.168.63.66', '192.0.2.66'))
            updated, _ = pod_and_maps(build(root))
        new_pod = updated['spec']['template']['spec']
        new_volumes = {volume['name']: volume for volume in new_pod['volumes']}
        self.assertNotEqual(self.container['envFrom'], new_pod['containers'][0]['envFrom'])
        for name in ['config', 'gateway-ca']:
            self.assertEqual(self.volumes[name], new_volumes[name])
        self.assertEqual(updated['spec']['updateStrategy']['type'], 'OnDelete')


if __name__ == '__main__':
    unittest.main()
