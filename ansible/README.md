# Ansible Automation for Frappe CRM

## Overview

This project automates the configuration and deployment of Frappe CRM using Ansible and Docker Compose.

## Technology Stack

- Ansible Core
- Ubuntu 26.04 LTS
- Docker Desktop
- Docker Compose
- MariaDB 10.8
- Redis
- Frappe Bench
- Ansible Vault

## Project Structure

```text
ansible/
├── ansible.cfg
├── inventory/
│   ├── hosts.ini
│   └── group_vars/
│       ├── all.yml
│       └── vault.yml
├── playbooks/
│   └── site.yml
├── roles/
│   ├── common/
│   │   └── tasks/main.yml
│   ├── docker/
│   │   └── tasks/main.yml
│   └── frappe/
│       ├── tasks/main.yml
│       └── templates/
│           ├── docker-compose.yml.j2
│           └── init.sh.j2
└── README.md
```

## Prerequisites

- Ubuntu or another supported Linux environment
- Python 3 and pip
- Ansible Core
- Docker Engine or Docker Desktop with Docker Compose
- A user with sudo privileges

## Setup

Activate the Python virtual environment:

```bash
source ~/task7-manas/.venv/bin/activate
```

Navigate to the repository root:

```bash
cd ~/task7-manas/internship-repo
```

## Configuration

Update deployment variables in:

`ansible/inventory/group_vars/all.yml`

Sensitive credentials are stored in the encrypted Ansible Vault file:

`ansible/inventory/group_vars/vault.yml`

Create or edit the encrypted file:

```bash
ansible-vault create ansible/inventory/group_vars/vault.yml
```

Never commit plaintext passwords or Vault password files.

## Run the Playbook

Validate syntax:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml --syntax-check --ask-vault-pass
```

Deploy Frappe CRM:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml --ask-vault-pass --ask-become-pass
```

## Verify Deployment

```bash
/usr/bin/docker compose -f /home/mehro/frappe-crm-ansible/docker-compose.yml ps
```

Services:

| Service | Port |
|---|---|
| Frappe CRM | 8000 |
| Socket.IO | 9000 |
| MariaDB | 3306 |
| Redis | 6379 |

Open the CRM at:

http://localhost:8000

## Idempotency

Run the playbook again:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml --ask-vault-pass --ask-become-pass
```

Ansible uses declarative tasks and Docker Compose reconciliation to avoid unnecessary changes.

## Roles

### Common
- Updates the APT package cache.
- Installs essential system dependencies.

### Docker
- Verifies Docker CLI availability.
- Checks Docker daemon connectivity.
- Verifies Docker Compose availability.

### Frappe
- Creates deployment directories.
- Manages directory permissions.
- Generates Docker Compose configuration.
- Generates the Frappe initialization script.
- Validates Compose configuration.
- Starts and manages application services.

## Security

- Ansible Vault encrypts sensitive credentials.
- Generated Compose configuration uses restrictive file permissions.
- Vault passwords must never be committed to Git.
- Do not share plaintext credentials in logs or screenshots.

## Author

Manas Mehrotra

DevOps Internship – Task 7
