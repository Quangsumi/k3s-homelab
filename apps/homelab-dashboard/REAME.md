## 3. Create the Kubernetes read-only credential

From this directory on an administrator machine, using the intended kube-vip
context:

~~~sh
kubectl --context kube-vip apply -f deploy/kubernetes-rbac.yaml
~~~

The manifest creates a ServiceAccount in kube-system and a ClusterRoleBinding.
It permits only get/list of core nodes and metrics.k8s.io nodes.

Choose **one** token lifecycle:

**Renewable token:** create a short-lived token, then arrange to replace it in
the Pi env file and recreate Caddy before it expires. The server can choose a
different lifetime from the requested duration.

~~~sh
kubectl --context kube-vip -n kube-system create token homelab-dashboard --duration=24h
~~~

**Optional persistent appliance token:** if regular renewal is unsuitable,
apply the separate non-expiring token Secret, then retrieve its generated token
(the decoding command below uses a Linux shell):

~~~sh
kubectl --context kube-vip apply -f deploy/kubernetes-persistent-token.optional.yaml
kubectl --context kube-vip -n kube-system get secret homelab-dashboard-token -o jsonpath='{.data.token}' | base64 --decode
~~~

Secret population is asynchronous; retry retrieval if the token is initially
empty. These retrieval commands print a credential: run them privately and
store the result only in the Pi env file or your secret manager.
Delete the token Secret to revoke a persistent token. Caddy cannot renew tokens
automatically. Do not use a cluster-admin kubeconfig, client key or K3s server token.

Verify the ServiceAccount's permissions:

~~~sh
kubectl --context kube-vip auth can-i list nodes --as=system:serviceaccount:kube-system:homelab-dashboard
kubectl --context kube-vip auth can-i list nodes.metrics.k8s.io --as=system:serviceaccount:kube-system:homelab-dashboard
kubectl --context kube-vip auth can-i list secrets --as=system:serviceaccount:kube-system:homelab-dashboard
~~~

Expected answers: yes, yes, no. Successful admin API reads alone do not validate
the dashboard's credential.