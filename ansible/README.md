# Frappe CRM Ansible Automation

## Overview

This project uses Ansible to automate the basic environment setup for Frappe CRM on an Ubuntu 22.04 Multipass virtual machine.

## Project Structure

```text
ansible/
├── inventory.ini
├── ansible.cfg
├── setup.yml
├── README.md
└── roles/
    ├── dependencies/
    │   └── tasks/main.yml
    ├── docker/
    │   └── tasks/main.yml
    └── frappe/
        └── tasks/main.yml
```

## Prerequisites

- Ubuntu 22.04 VM using Multipass
- Ansible
- Internet connection

## Ansible Roles

- **dependencies:** Installs required packages such as Git, curl, wget, and certificates.
- **docker:** Installs Docker and Docker Compose, and enables the Docker service.
- **frappe:** Creates the Frappe CRM directory and downloads the Docker Compose configuration.

## How to Run

Open the Multipass VM and navigate to the Ansible directory:

```bash
cd ~/ansible
```

Check the playbook syntax:

```bash
ansible-playbook -i inventory.ini setup.yml --syntax-check
```

Run the playbook:

```bash
ansible-playbook -i inventory.ini setup.yml
```

## Idempotency Testing

Run the playbook a second time:

```bash
ansible-playbook -i inventory.ini setup.yml
```

Second-run result:

```text
ok=6  changed=0  unreachable=0  failed=0
```

This confirms that rerunning the playbook does not make unnecessary changes.

## Verification

Check Docker and Docker Compose:

```bash
docker --version
docker compose version
```

Check the downloaded configuration:

```bash
ls -l /opt/frappe-crm/
```

## Current Status

- Ansible playbook executed successfully.
- Docker and Docker Compose installed.
- Frappe CRM Docker Compose configuration downloaded.
- Idempotency verified.
- Frappe CRM container deployment and application startup are not yet verified.

## Evidence

Screenshots of the successful playbook execution and idempotency test can be attached to the GitHub Pull Request.