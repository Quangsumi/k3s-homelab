```
kubectl -n postgres get externalsecret postgres-credentials
kubectl -n postgres get secret postgres-secret-infisical

kubectl -n postgres get secret postgres-secret-infisical \
  -o go-template='{{range $key,$value := .data}}{{printf "%s\n" $key}}{{end}}'
```
### Force the ClusterExternalSecret to update its generated ExternalSecrets:
```
kubectl annotate clusterexternalsecret lab-wildcard-tls \
  external-secrets.io/force-sync="$(date +%s)" \
  --overwrite

kubectl get externalsecret -A
```