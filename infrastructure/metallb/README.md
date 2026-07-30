# MetalLB

```powershell
kubectl -n metallb-system get pods
kubectl -n metallb-system get ipaddresspool,l2advertisement
```

MetalLB advertises LAN addresses. Tailscale provides private Tailnet ingress;
the two systems serve different entry paths and can coexist.

## Troubleshooting Wi-Fi layer-2 advertisement

Some Wi-Fi interfaces or drivers may require promiscuous mode for L2
advertisement. Treat this as a node-level diagnostic, not a default GitOps
step:

```bash
sudo ip link set wlan0 promisc on
```

If advertisement must be pinned to a stable node, add a `nodeSelectors` rule to
`10-l2advertisement.yaml`, for example:

```yaml
nodeSelectors:
  - matchLabels:
      kubernetes.io/hostname: rpivn
```

Then let Argo CD show and apply the manifest change. Avoid deleting all MetalLB
pods as a routine step; first inspect controller and speaker events and restart
only the affected workload when diagnosis requires it.