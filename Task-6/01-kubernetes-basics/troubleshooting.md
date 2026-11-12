# Kubernetes Troubleshooting

## Common Pod States

| Status | Meaning |
|---|---|
| Pending | Pod is waiting for scheduling or resources |
| ContainerCreating | Container setup is in progress |
| Running | Pod is running |
| CrashLoopBackOff | Container repeatedly fails and restarts |
| ImagePullBackOff | Kubernetes cannot pull the container image |
| ErrImagePull | Image retrieval failed |
| OOMKilled | Container exceeded its memory limit |

## Troubleshooting Workflow

1. Check pod status.
2. Inspect pod events.
3. Review container logs.
4. Verify image names and pull credentials.
5. Check resource requests and limits.
6. Verify Service selectors and endpoints.
7. Check application connectivity.

## Useful Commands

```bash
kubectl get pods -A

kubectl describe pod <pod-name> -n <namespace>

kubectl logs <pod-name> -n <namespace>

kubectl logs <pod-name> -n <namespace> --previous

kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp

kubectl get services -n <namespace>

kubectl get endpoints -n <namespace>

kubectl top pods -n <namespace>
```

## Common Problems

### ImagePullBackOff
Check the image name, tag and registry access.

### CrashLoopBackOff
Inspect current and previous container logs. Check application configuration and startup commands.

### Pending Pod
Inspect scheduling events, available resources, PVC status and node constraints.

### Service Not Accessible
Check Service selectors, target ports, endpoints and network policies.

### Database Connection Failure
Check database pod health, Service DNS name, credentials and network connectivity.

## Conclusion

Kubernetes troubleshooting requires checking the pod, deployment, logs, events, networking and storage rather than assuming every issue is an application bug.