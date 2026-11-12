# Kubernetes Cluster Architecture

## Overview

A Kubernetes cluster is composed of a Control Plane and one or more Worker Nodes.

The Control Plane manages the cluster, while Worker Nodes run application workloads.

(k8s-diagram.png)

## Control Plane Components

1. **API Server:** Handles Kubernetes API requests.
2. **etcd:** Stores cluster state and configuration.
3. **Scheduler:** Assigns pending pods to suitable nodes.
4. **Controller Manager:** Reconciles the actual state with the desired state.
5. **Cloud Controller Manager:** Integrates cloud infrastructure with Kubernetes.

## Worker Node Components

1. **Kubelet:** Ensures containers described in pod specifications are running.
2. **Container Runtime:** Executes containers.
3. **Kube-proxy:** Provides Service networking functionality where used.

## Cluster Workflow

1. A user submits a deployment manifest using kubectl.
2. The API Server validates the request.
3. The desired state is stored in etcd.
4. The Scheduler selects a suitable worker node.
5. The Kubelet instructs the container runtime to start the containers.
6. Controllers monitor and maintain the desired state.

## Key Difference

| Control Plane | Worker Node |
|---|---|
| Manages the cluster | Runs application workloads |
| Schedules pods | Hosts pods |
| Maintains desired state | Reports workload status |
| Runs API Server and controllers | Runs kubelet and container runtime |