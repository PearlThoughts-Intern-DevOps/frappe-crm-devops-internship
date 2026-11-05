# Task 1 – Frappe CRM Project Exploration

## Overview

This document describes my exploration of the Frappe CRM project as part of the DevOps internship Task 1.

The objective was to understand the project structure, identify the technologies used, run the application locally, and document the setup and troubleshooting experience.

## Objectives

- Clone and explore the Frappe CRM repository.
- Understand the project directory structure.
- Identify the main technologies and tools used.
- Set up and run the application locally using Docker.
- Observe the application and its supporting services.
- Document the setup process and troubleshooting findings.

## Technologies and Tools

- **Frappe Framework:** Python-based framework used by the application.
- **Frappe CRM:** Customer Relationship Management application.
- **Python:** Backend programming language.
- **MariaDB:** Relational database.
- **Redis:** Supporting service used by the Frappe environment.
- **Docker:** Containerization platform.
- **Docker Compose:** Used to manage the application's containers.
- **Git and GitHub:** Source code management and collaboration.
- **Visual Studio Code:** Code editor used for project exploration.

## Project Exploration

I explored the repository to understand its application code, configuration files, frontend resources, documentation, and Docker-related setup.

I also reviewed the Docker Compose configuration and inspected the containers, logs, volumes, and application configuration during local setup.

## Local Setup and Troubleshooting

During the local setup, I worked with Docker Desktop and WSL2 and investigated issues encountered during initialization.

Some of the issues investigated included:

- Shell script line-ending problems (CRLF).
- MariaDB SSL/TLS connection errors.
- Missing database tables during Frappe site initialization.
- Container logs and service status.
- Docker volumes and persistence of application data.

These troubleshooting activities helped me understand how the application services interact and how to investigate containerized application startup problems.

## Important Commands Used

```powershell
git clone <repository-url>
cd frappe-crm-devops-internship
docker compose config
docker compose up -d
docker compose ps
docker compose logs
docker ps -a
docker volume ls
docker network ls
```

## Deliverables

1. `TASK1_PROJECT_EXPLORATION.docx` – Project exploration documentation.
2. `TASK1_README.md` – Summary of the project exploration and setup.

## Conclusion

This task provided practical exposure to the Frappe CRM project structure, Docker-based application setup, container inspection, database initialization, and troubleshooting.

It also improved my understanding of how multiple services work together in a containerized application environment.