# normal-ass-note Kubernetes

The deployment uses `quangsumi/normal-ass-note:latest`.

Before applying, replace the placeholder values in `secret.yaml`:

- `ConnectionStrings__DefaultConnection`
- `Jwt__SigningKey`

Deploy:

```powershell
kubectl apply -k k8n
kubectl -n normal-ass-note rollout status deployment/normal-ass-note
```

Open it locally through the cluster service:

```powershell
kubectl -n normal-ass-note port-forward svc/normal-ass-note 8080:80
```

Then browse to `http://localhost:8080`.
