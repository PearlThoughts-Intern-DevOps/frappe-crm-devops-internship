# Kubernetes Pods and Deployments

## Pods

A Pod is the smallest deployable unit in Kubernetes. It can contain one or more containers that share networking and storage resources.

Key points:
- Pods receive unique IP addresses.
- Containers in the same pod can communicate using localhost.
- Pods are replaceable and their IP addresses may change.

## Deployments

A Deployment manages a set of identical application pods.

Responsibilities:
- Maintains the desired number of replicas.
- Recreates pods when they fail.
- Supports rolling updates.
- Allows rollback to previous revisions.

## Example Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx-demo
  template:
    metadata:
      labels:
        app: nginx-demo
    spec:
      containers:
        - name: nginx
          image: nginx:latest
          ports:
            - containerPort: 80
```

## Useful Commands

```bash
kubectl apply -f deployment.yaml
kubectl get deployments
kubectl get pods
kubectl describe deployment nginx-demo
kubectl scale deployment nginx-demo --replicas=3
kubectl rollout status deployment/nginx-demo
kubectl rollout history deployment/nginx-demo
```