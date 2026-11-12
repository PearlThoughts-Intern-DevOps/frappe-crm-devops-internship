# Kubernetes Services and Networking

## Overview

Kubernetes Services provide stable network access to a group of pods.

Pods can be replaced, causing their IP addresses to change. Services provide a stable endpoint.

## Service Types

### ClusterIP
Provides internal access within the Kubernetes cluster. This is the default Service type.

### NodePort
Exposes an application through a port on each worker node.

### LoadBalancer
Integrates with a supported cloud provider to provision an external load balancer.

### Ingress
Provides HTTP/HTTPS routing to services based on hostnames and paths through an Ingress Controller.

## Example ClusterIP Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  type: ClusterIP
  selector:
    app: nginx-demo
  ports:
    - port: 80
      targetPort: 80
```

## Useful Commands

```bash
kubectl get services
kubectl describe service nginx-service
kubectl get endpoints nginx-service
kubectl port-forward service/nginx-service 8080:80
```