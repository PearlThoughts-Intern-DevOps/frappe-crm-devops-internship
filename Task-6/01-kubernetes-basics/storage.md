# Kubernetes Persistent Storage

## Overview

Containers and pods can be replaced. Applications that store important data need persistent storage.

Kubernetes provides Persistent Volumes, Persistent Volume Claims and StorageClasses.

## Persistent Volume (PV)

A PV represents storage available to the Kubernetes cluster.

It can be backed by cloud disks or other supported storage systems.

## Persistent Volume Claim (PVC)

A PVC is a request for storage by an application.

A PVC requests properties such as storage capacity and access mode.

## StorageClass

A StorageClass defines how storage is dynamically provisioned.

For example, a cloud storage provisioner can create an EBS volume when a PVC requests storage.

## Storage Workflow

1. An administrator or provisioner makes storage available.
2. An application creates a PVC.
3. Kubernetes binds the PVC to a suitable PV.
4. A pod mounts the claimed storage.
5. Application data can persist beyond the lifetime of an individual pod.

## Example PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-storage
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

## Important Considerations

- Stateful applications such as MariaDB need persistent storage.
- Deleting a pod does not necessarily delete its PVC.
- PV reclaim policies determine what happens to storage after claim deletion.
- StorageClass and CSI driver configuration must match the underlying storage environment.