#!/usr/bin/env python3
"""Render GitOps sources and check ownership/project boundaries without a cluster."""
import argparse
from fnmatch import fnmatchcase
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/Quangsumi/k3s-homelab.git'
SERVER = 'https://kubernetes.default.svc'
# Fail closed for unknown resource scopes. Extend this map or supply a CRD when
# introducing a new kind; otherwise project permission checks could miss it.
SCOPES = {}
for group, kinds in {
    '': 'Namespace Node PersistentVolume',
    'rbac.authorization.k8s.io': 'ClusterRole ClusterRoleBinding',
    'scheduling.k8s.io': 'PriorityClass',
    'storage.k8s.io': 'StorageClass CSIDriver CSINode VolumeAttachment',
    'apiextensions.k8s.io': 'CustomResourceDefinition',
    'admissionregistration.k8s.io': 'MutatingWebhookConfiguration ValidatingWebhookConfiguration',
    'apiregistration.k8s.io': 'APIService',
    'networking.k8s.io': 'IngressClass',
    'cert-manager.io': 'ClusterIssuer',
    'trust.cert-manager.io': 'Bundle',
    'external-secrets.io': 'ClusterSecretStore ClusterExternalSecret ClusterPushSecret',
    'tailscale.com': 'ProxyClass ProxyGroup',
}.items():
    SCOPES.update({(group, kind): False for kind in kinds.split()})
for group, kinds in {
    '': 'Pod Service ServiceAccount Secret ConfigMap Endpoints PersistentVolumeClaim ReplicationController ResourceQuota LimitRange',
    'apps': 'Deployment DaemonSet StatefulSet ReplicaSet ControllerRevision',
    'batch': 'Job CronJob',
    'rbac.authorization.k8s.io': 'Role RoleBinding',
    'networking.k8s.io': 'Ingress NetworkPolicy',
    'discovery.k8s.io': 'EndpointSlice',
    'policy': 'PodDisruptionBudget',
    'autoscaling': 'HorizontalPodAutoscaler',
    'argoproj.io': 'Application AppProject ApplicationSet',
    'cert-manager.io': 'Certificate CertificateRequest Issuer',
    'acme.cert-manager.io': 'Order Challenge',
    'external-secrets.io': 'ExternalSecret SecretStore PushSecret',
    'traefik.io': 'IngressRoute IngressRouteTCP Middleware MiddlewareTCP ServersTransport ServersTransportTCP TLSOption TLSStore',
    'helm.cattle.io': 'HelmChart HelmChartConfig',
    'metallb.io': 'IPAddressPool L2Advertisement BGPAdvertisement BGPPeer BFDProfile Community',
}.items():
    SCOPES.update({(group, kind): True for kind in kinds.split()})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(command):
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    require(result.returncode == 0, f'{command[0]} failed: {result.stderr.strip()}')
    return result.stdout


def documents(text):
    return [obj for obj in yaml.safe_load_all(text) if obj]


def load(path):
    return yaml.safe_load((ROOT / path).read_text())


def group_kind(obj):
    return (obj['apiVersion'].split('/')[0] if '/' in obj['apiVersion'] else '', obj['kind'])


def namespaced(obj):
    key = group_kind(obj)
    require(key in SCOPES, f'Unknown resource scope: {key}; add its CRD or scope mapping')
    return SCOPES[key]


def allowed(value, patterns):
    return any(fnmatchcase(value, p) for p in patterns if not p.startswith('!')) and not any(
        fnmatchcase(value, p[1:]) for p in patterns if p.startswith('!'))


def matches(obj, rules):
    group, kind = group_kind(obj)
    return any(fnmatchcase(group, r['group']) and fnmatchcase(kind, r['kind'])
               and fnmatchcase(obj['metadata']['name'], r.get('name', '*')) for r in rules)


def check_resource(obj, app, project):
    spec = project['spec']
    label = f"{app['metadata']['name']}: {obj['kind']}/{obj['metadata']['name']}"
    if namespaced(obj):
        namespace = obj['metadata'].get('namespace', app['spec']['destination']['namespace'])
        destinations = [d for d in spec['destinations'] if d['server'] == SERVER]
        require(allowed(namespace, [d['namespace'] for d in destinations]), f'{label}: namespace {namespace} not permitted')
        require('namespaceResourceWhitelist' not in spec or matches(obj, spec['namespaceResourceWhitelist']), f'{label}: namespaced kind not permitted')
        require(not matches(obj, spec.get('namespaceResourceBlacklist', [])), f'{label}: namespaced kind denied')
    else:
        require(matches(obj, spec.get('clusterResourceWhitelist', [])), f'{label}: cluster kind not permitted')
        require(not matches(obj, spec.get('clusterResourceBlacklist', [])), f'{label}: cluster kind denied')


def helm_render(source, app, directory, index):
    helm = source.get('helm', {})
    command = ['helm', 'template', helm.get('releaseName', app['metadata']['name']), source['chart'],
               '--repo', source['repoURL'], '--version', str(source['targetRevision']),
               '--namespace', app['spec']['destination']['namespace'], '--include-crds',
               '--kube-version', '1.34.0', '--repository-config', str(directory / 'repositories.yaml'),
               '--repository-cache', str(directory / 'repository')]
    for value_file in helm.get('valueFiles', []):
        require(value_file.startswith('$'), f'Unsupported chart-relative values file: {value_file}')
        ref, relative = value_file[1:].split('/', 1)
        require(any(s.get('ref') == ref and s['repoURL'] == REPO for s in app['spec'].get('sources', [])), f'Unknown values ref: {ref}')
        file_path = (ROOT / relative).resolve()
        require(file_path.is_relative_to(ROOT) and file_path.is_file(), f'Missing values file: {relative}')
        command += ['--values', str(file_path)]
    for field in ('values', 'valuesObject'):
        if field in helm:
            path = directory / f'values-{index}-{field}.yaml'
            path.write_text(helm[field] if field == 'values' else yaml.safe_dump(helm[field]))
            command += ['--values', str(path)]
    require(not helm.get('parameters'), 'Add Helm parameters support to this validator before using them')
    return documents(run(command))


def priority_references(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ('priorityClassName', 'priorityClass') and isinstance(value, str) and value:
                yield value
            yield from priority_references(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from priority_references(value)


def validate(args):
    renderer = [args.kustomize, 'build'] if args.kustomize else (
        ['kustomize', 'build'] if shutil.which('kustomize') else ['kubectl', 'kustomize'])
    rendered = {}
    for path in sorted(ROOT.rglob('kustomization.yaml')):
        relative = str(path.parent.relative_to(ROOT))
        rendered[relative] = documents(run(renderer + [relative]))
    control = rendered['bootstrap/homelab']
    require(all(obj['kind'] in ('Application', 'AppProject') for obj in control), 'Bootstrap must contain only Applications and AppProjects')
    projects = {obj['metadata']['name']: obj for obj in control if obj['kind'] == 'AppProject'}
    seed_project = load('bootstrap/bootstrap-project.yaml')
    projects[seed_project['metadata']['name']] = seed_project
    root_app = load('bootstrap/root-application.yaml')
    require(root_app['spec']['project'] == seed_project['metadata']['name'], 'Root must use the restricted bootstrap project')
    require(root_app['spec']['source'] == {'repoURL': REPO, 'targetRevision': 'main', 'path': 'bootstrap/homelab'}, 'Unexpected root source')
    require(root_app['spec']['destination'] == {'server': SERVER, 'namespace': 'argocd'}, 'Unexpected root destination')
    require(root_app['metadata']['name'] not in [o['metadata']['name'] for o in control], 'Seed Application must not manage itself')
    for obj in control:
        check_resource(obj, root_app, seed_project)
    apps = [obj for obj in control if obj['kind'] == 'Application']
    require(len({a['metadata']['name'] for a in apps}) == len(apps), 'Duplicate Application names')
    local_paths, resources, ownership = set(), [], {}
    with tempfile.TemporaryDirectory(prefix='homelab-gitops-') as temp:
        directory = Path(temp)
        for app in apps:
            name, spec = app['metadata']['name'], app['spec']
            require(spec['project'] in projects, f'{name}: unknown project')
            project = projects[spec['project']]
            require(spec['destination']['server'] == SERVER, f'{name}: unexpected cluster')
            require(allowed(spec['destination']['namespace'], [d['namespace'] for d in project['spec']['destinations'] if d['server'] == SERVER]), f'{name}: destination not permitted')
            app_resources = []
            sources = spec.get('sources', [spec['source']] if 'source' in spec else [])
            for index, source in enumerate(sources):
                require(allowed(source['repoURL'], project['spec']['sourceRepos']), f'{name}: repository not permitted')
                if source['repoURL'] == REPO:
                    require(source['targetRevision'] == 'main', f'{name}: unexpected Git revision')
                    if 'path' in source:
                        path = source['path']
                        require(path in rendered, f'{name}: missing Kustomize source {path}')
                        local_paths.add(path)
                        app_resources += rendered[path]
                elif 'chart' in source:
                    revision = str(source.get('targetRevision', ''))
                    require(revision and not any(c in revision for c in '*<>=~^'), f'{name}: chart must be pinned')
                    if args.helm:
                        app_resources += helm_render(source, app, directory, index)
                else:
                    raise ValueError(f'{name}: unsupported source')
            for obj in app_resources:
                if obj['kind'] == 'CustomResourceDefinition':
                    crd = obj['spec']
                    SCOPES[(crd['group'], crd['names']['kind'])] = crd['scope'] == 'Namespaced'
            for obj in app_resources:
                require(obj['kind'] not in ('Application', 'AppProject', 'ApplicationSet'), f'{name}: child source must not manage Argo CD control objects')
                check_resource(obj, app, project)
                metadata = obj['metadata']
                namespace = metadata.get('namespace', spec['destination']['namespace']) if namespaced(obj) else ''
                identity = (*group_kind(obj), namespace, metadata['name'])
                require(identity not in ownership, f'{name}: duplicate ownership {identity} (also {ownership.get(identity)})')
                ownership[identity] = name
                if name == 'tailscale':
                    require(not (obj['kind'] == 'Secret' and metadata['name'] == 'operator-oauth'), 'Helm must not own ESO OAuth Secret')
                resources.append(obj)
            print(f'OK {name}: {len(app_resources)} rendered resources', flush=True)
    # Top-level deployable packages must be listed, not silently omitted.
    expected = {str(p.parent.relative_to(ROOT)) for base in ('apps', 'infrastructure') for p in (ROOT / base).glob('*/kustomization.yaml')}
    expected.update(('external-services', 'rbac', 'infrastructure/cert-manager/infisical-acme', 'infrastructure/tailscale/credentials'))
    require(expected <= local_paths, f'Packages missing from bootstrap: {sorted(expected - local_paths)}')
    priorities = {o['metadata']['name'] for o in resources if o['kind'] == 'PriorityClass'}
    priorities.update(('system-cluster-critical', 'system-node-critical'))
    missing = {p for obj in resources for p in priority_references(obj)} - priorities
    require(not missing, f'Undefined PriorityClasses: {sorted(missing)}')
    print(f'Validated {len(rendered)} Kustomizations, {len(apps)} Applications and project/ownership/priority boundaries' + (' including Helm charts.' if args.helm else ' (Helm skipped; use --helm).'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kustomize', help='Path to the Kustomize binary')
    parser.add_argument('--helm', action='store_true', help='Download and render every pinned chart as well')
    try:
        validate(parser.parse_args())
    except (ValueError, OSError, yaml.YAMLError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
