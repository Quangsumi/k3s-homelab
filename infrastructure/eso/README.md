```
kubectl -n postgres get externalsecret postgres-credentials
kubectl -n postgres get secret postgres-secret-infisical

kubectl -n postgres get secret postgres-secret-infisical \
  -o go-template='{{range $key,$value := .data}}{{printf "%s\n" $key}}{{end}}'
```