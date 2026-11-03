# Understanding Frappe CRM Project

# Services in Our Project

The Compose file defines five services:

| Service | Purpose |
|---|---|
| MariaDB | Stores application data. |
| Redis Cache | Helps store frequently used data temporarily. |
| Redis Queue | Manages background jobs. |
| Redis Socket.IO | Supports real-time communication. |
| Frappe | Provides the development environment for the application. |

##  Understanding Important Docker Compose Configurations

### A. Image

Example:

```yaml
image: mariadb:10.6
```

An image is a package used to create a Docker container. Here, Docker uses MariaDB version 10.6.

### B. Environment Variables

Example:

```yaml
environment:
  MYSQL_ROOT_PASSWORD: 123
```

Environment variables provide configuration values to a container. Here, the MariaDB root password is set to `123`.

### C. Volume

Example:

```yaml
volumes:
  - mariadb-data:/var/lib/mysql
```

A volume stores database data outside the container's writable layer. This helps preserve data even if the container is removed and recreated.

### D. Bind Mount

Example:

```yaml
volumes:
  - ..:/workspace:cached
```

A bind mount connects a folder from my computer to a folder inside the container.

In this project, the parent folder of the Compose file's directory is shared with the container at `/workspace`.

This allows the container to access project files from my computer.

### E. Working Directory

Example:

```yaml
working_dir: /workspace/frappe-bench
```

This specifies the default directory where commands run inside the Frappe container.

### F. Ports

Example:

```yaml
ports:
  - 8000-8005:8000-8005
  - 9000-9005:9000-9005
```

Port mapping allows services inside a container to be accessed through ports on my computer.

### G. Command

Example:

```yaml
command: sleep infinity
```

This keeps the Frappe development container running instead of exiting immediately.

## What I Learned

During this exploration, I learned:

1. How Docker Compose manages multiple services.
2. The purpose of MariaDB and Redis services.
3. The difference between Docker images and containers.
4. How named volumes preserve database data.
5. How bind mounts share project files with containers.
6. How environment variables, ports and working directories are configured.


I learned how different services are defined and how Docker connects storage and project files to containers.

