# Frappe CRM – Project Exploration, Local Setup and Troubleshooting

**Internship:** PearlThoughts – DevOps Internship  
**Task:** Task 1 – Explore and Run Frappe CRM Locally  
**Environment:** Ubuntu (WSL), Docker and Docker Compose

The project contains separate folders for application code, frontend resources, Docker configuration and documentation.

## 1. Understanding Docker Compose

I identified the Docker Compose file used for the local setup:

`docker/docker-compose.yml`

Docker Compose helps run multiple services together using a single YAML configuration file.

Our project uses three main services:

| Service | Docker image | Purpose |
|---|---|---|
| Frappe | `frappe/bench:latest` | Runs the CRM application. |
| MariaDB | `mariadb:10.8` | Stores application data. |
| Redis | `redis:alpine` | Supports caching and background jobs. |

### 1.1 Frappe service

Frappe is the application service that runs our CRM.

It uses the `frappe/bench:latest` Docker image.

Important configuration:

- Port `8000` is used to access the web application.
- Port `9000` is used for realtime communication.
- The application initialisation script is executed using `bash /workspace/init.sh`.

### 1.2 MariaDB service

MariaDB is the database service.

It stores the information required by the CRM application.

The configuration uses:

- MariaDB version 10.8.
- A root password for local development.
- A named Docker volume called `mariadb-data`.

The named volume helps preserve database data even when the MariaDB container is recreated.

### 1.3 Redis service

Redis is used for caching and queue-related operations.

It helps the application manage certain background tasks and temporary data.

## 2. Understanding the init.sh file

The file `docker/init.sh` contains commands to initialise the Frappe environment.

The main operations performed by this script are:

1. Checks whether a Frappe Bench directory already exists.
2. Creates a new Bench environment if required.
3. Configures MariaDB as the database host.
4. Configures Redis for cache, queue and Socket.IO.
5. Downloads the CRM application using `bench get-app`.
6. Creates a new site called `crm.localhost`.
7. Installs the CRM application on the site.
8. Enables developer mode and other development settings.
9. Starts the Frappe application using `bench start`.

**What is Bench?**

Bench is a command-line tool used to manage Frappe environments, applications and sites.

## 3. Running Frappe CRM locally

Before starting the application, I checked whether Docker was installed and running.

### Step 1: Check Docker installation

```bash
docker --version
docker compose version
docker info
```

These commands helped verify Docker, Docker Compose and Docker Engine availability.

### Step 2: Validate the Docker Compose configuration

```bash
docker compose -f docker/docker-compose.yml config
```

This command checks and displays the resolved Compose configuration.

It helped verify that the YAML configuration was valid.

### Step 3: Start the application

```bash
docker compose -f docker/docker-compose.yml up
```

This command starts the services defined in the Compose file.

### Step 4: Access the application

I tried accessing:

`http://localhost:8000`

Initially, the application did not load successfully.

This led us to investigate the issue.

---

## 5. Troubleshooting

During the local setup, I encountered an HTTP 500 Internal Server Error.

Although the containers were running, the application was not working correctly.

I followed a step-by-step troubleshooting process.

### Problem 1: Application was not opening

The CRM website did not load successfully in the browser.

I checked the container status.

```bash
docker compose -f docker/docker-compose.yml ps
```

The Frappe, MariaDB and Redis containers were running.


### Problem 2: HTTP 500 Internal Server Error

I tested the application using:

```bash
curl -I http://localhost:8000
```

The response showed:

```text
HTTP/1.1 500 INTERNAL SERVER ERROR
```

I checked the Frappe logs:

```bash
docker compose -f docker/docker-compose.yml logs frappe --tail=50
```

The logs showed missing database tables.

### Problem 3: Missing database tables

The logs showed errors such as:

```text
Table '...tabSingles' doesn't exist
Table '...tabDocType' doesn't exist
```

Frappe requires database tables to store its application information.

- `tabDocType` stores information about the structure and metadata of application document types.
- `tabSingles` stores values for single-record DocTypes.

The missing tables indicated that the site/database initialisation had not completed successfully.

### Problem 4: Checking the site directory and Bench commands

I checked whether the site directory existed:

```bash
docker compose -f docker/docker-compose.yml exec frappe ls -la /home/frappe/frappe-bench/sites
```

The `crm.localhost` directory was present.

However, the presence of the directory did not guarantee that its database schema was completely initialised.

I also tried running:

```bash
docker compose -f docker/docker-compose.yml exec frappe bench list-apps
```

This failed because the command was executed outside the Bench directory.

I corrected it by specifying the working directory:

```bash
docker compose -f docker/docker-compose.yml exec -w /home/frappe/frappe-bench frappe bench --site crm.localhost list-apps
```

The command still reported missing database tables.

### Problem 5: Discovering the MariaDB SSL/TLS error

I filtered the application logs to identify installation and database errors.

```bash
docker compose -f docker/docker-compose.yml logs frappe | grep -iE "new-site|install-app|Traceback|ERROR|Error|Failed|successfully"
```

I discovered this error:

```text
TLS/SSL error: SSL is required, but the server does not support it
```

I also checked the MariaDB client and server versions.

- MariaDB client inside Frappe
I also checked the MariaDB client and server versions.

MariaDB client inside Frappe: 11.8.6

MariaDB server: 10.8.8

The logs suggested a mismatch between the SSL connection requested by the client and the server's SSL support/configuration in our local environment.

## Problem 6: Fixing the MariaDB client configuration

To address the SSL connection issue, I created a configuration file:

nano docker/mariadb-client.cnf

Added the following content:

[client]
skip-ssl

Explanation:

[client] specifies that the setting applies to MariaDB client programs.

skip-ssl tells the client not to use SSL for this local development connection.

Then I mounted this file into the Frappe container through the Docker Compose configuration:

volumes:
  - .:/workspace
  - ./mariadb-client.cnf:/etc/mysql/mariadb.conf.d/client.cnf:ro

Explanation:

The first path refers to the file on the host machine.

The second path is where the file is available inside the container.

ro means read-only.

This is an example of a Docker bind mount.

Note: Disabling SSL is only a workaround for this isolated local development environment. Production database connections should use properly configured TLS encryption.

## Problem 7: Recreating the Frappe container

After modifying the configuration, I validated the Compose file:

docker compose -f docker/docker-compose.yml config

Then I recreated the Frappe container:

docker compose -f docker/docker-compose.yml up -d --force-recreate frappe

This applied the updated configuration to the newly created Frappe container.

## Problem 8: Verifying the configuration

I checked whether the MariaDB client had loaded the new configuration:

docker compose -f docker/docker-compose.yml exec frappe mariadb --print-defaults

The output included:

--skip-ssl

This confirmed that the client configuration was loaded.

I then tested the database connection:

docker compose -f docker/docker-compose.yml exec frappe mariadb --host=mariadb --user=root --password --execute="SELECT VERSION();"

The database returned its version successfully.

This confirmed that the client could connect to the MariaDB server.

Final Verification

After fixing the configuration, I checked the application logs again:

docker compose -f docker/docker-compose.yml logs frappe --tail=100

This time, the logs showed successful initialisation and installation messages.

Some important messages included:

Installing Frappe.

Updating DocTypes for Frappe.

Installing CRM.

Updating DocTypes for CRM.

CRM custom fields installed.

Current site set to crm.localhost.

Web process started.

Socket.IO process started.

Scheduler and worker processes started.

Realtime service listening on port 9000.

Web server listening on port 8000.

Finally, I accessed:

http://localhost:8000

The CRM login page appeared, and I successfully logged in.

Result: Frappe CRM was successfully running locally using Docker Compose.

8. Important Docker Commands Learned

Command

Purpose

docker --version

Checks Docker version.

docker compose version

Checks Compose version.

docker info

Displays Docker Engine information.

docker compose ... config

Validates and displays Compose configuration.

docker compose ... up

Creates and starts services.

docker compose ... up -d

Starts services in the background.

docker compose ... ps

Checks container status.

docker compose ... logs

Displays container logs.

docker compose ... exec

Executes commands inside a running container.

docker compose ... up -d --force-recreate frappe

Recreates the Frappe service container.

curl -I

Checks the HTTP response headers from a URL.

grep

Searches text for matching patterns.