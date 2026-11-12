# Kubernetes Fundamentals

## Overview

Kubernetes is an open-source container orchestration platform used to deploy, manage, scale and monitor containerized applications.

It automates application deployment, scheduling, networking, scaling and recovery.

## Kubernetes Architecture

A Kubernetes cluster consists of two major components:

### 1. Control Plane

The Control Plane manages the overall Kubernetes cluster.

Its main components are:

- **API Server:** Entry point for communication with the Kubernetes cluster. It processes requests from kubectl and other components.
- **etcd:** Distributed key-value store that maintains cluster configuration and state.
- **Scheduler:** Selects suitable worker nodes for newly created pods.
- **Controller Manager:** Runs controllers that continuously monitor and maintain the desired cluster state.
- **Cloud Controller Manager:** Integrates Kubernetes with cloud provider infrastructure when applicable.

### 2. Worker Nodes

Worker nodes execute application workloads.

Their main components are:

- **Kubelet:** Communicates with the API Server and ensures assigned pods are running.
- **Container Runtime:** Runs containers, such as containerd.
- **Kube-proxy:** Implements Kubernetes Service networking rules where applicable.

## Core Kubernetes Objects

| Component | Description |
|---|---|
| Pod | Smallest deployable Kubernetes unit |
| Deployment | Manages application pods and replicas |
| Service | Provides stable network access to pods |
| ConfigMap | Stores non-sensitive configuration |
| Secret | Stores sensitive configuration data |
| Namespace | Provides logical separation of resources |
| Persistent Volume | Represents storage available to the cluster |
| Persistent Volume Claim | Requests storage for an application |
| StorageClass | Defines how storage can be dynamically provisioned |

## Application Deployment Architecture

A typical multi-component application can run using:

- Application pods for frontend and backend services.
- Database pods or externally managed database services.
- Redis for caching and background job queues.
- Background workers for asynchronous tasks.
- Scheduler for periodic jobs.
- Services for internal communication.
- Persistent storage for database and application files.

## Kubernetes Networking

Kubernetes provides networking between pods and services.

- Each pod receives its own cluster IP.
- Services provide stable access to changing pod IPs.
- ClusterIP is used for internal communication.
- NodePort exposes a service through a worker node port.
- LoadBalancer exposes a service through a cloud load balancer.
- Ingress provides HTTP/HTTPS routing through an Ingress Controller.

## Storage Concepts

- **Persistent Volume (PV):** A storage resource available to the cluster.
- **Persistent Volume Claim (PVC):** A request for storage by a workload.
- **StorageClass:** Defines storage provisioning parameters and provisioner.

Persistent storage is important for stateful applications such as databases because pod storage is not automatically durable across pod replacement.

## Configuration and Secrets

ConfigMaps separate non-sensitive configuration from container images.

Secrets are used to provide sensitive values such as database passwords and application credentials.

Sensitive values should not be committed to source control.

## Troubleshooting Commands

```bash
kubectl get nodes
kubectl get pods -A
kubectl get deployments -A
kubectl get services -A
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous
kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp
```

## Learning Outcomes

- Understanding Kubernetes architecture.
- Understanding Control Plane and Worker Node components.
- Learning core Kubernetes objects and their responsibilities.
- Understanding application networking and storage.
- Learning how to inspect pod health and troubleshoot failures.