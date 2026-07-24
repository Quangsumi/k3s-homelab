```
kubectl -n postgres get externalsecret postgres-credentials
kubectl -n postgres get secret postgres-secret-infisical

kubectl -n postgres get secret postgres-secret-infisical \
  -o go-template='{{range $key,$value := .data}}{{printf "%s\n" $key}}{{end}}'
```
### Force the ExternalSecret/ClusterExternalSecret to update its generated secrets:
```
kubectl annotate es <external-secret-name> force-sync=$(date +%s) --overwrite -n <namespace>

kubectl annotate clusterexternalsecret lab-wildcard-tls \
  external-secrets.io/force-sync="$(date +%s)" \
  --overwrite

kubectl get externalsecret -A
```