# Ansible Automation for Frappe CRM

Ansible roles and playbooks that prepare a server and deploy Frappe CRM with Docker: install packages, install Docker, create directories, manage configuration files, and start the services.

## Architecture

- **Control node:** has Ansible installed and runs the playbooks.
- **Target node:** configured by Ansible. Frappe CRM runs here in Docker.

Both are Ubuntu 26.04 LTS EC2 instances in the same VPC. The control node connects to the target over SSH using its private IP.

## Project structure

```
.
├── ansible.cfg
├── inventory/
│   ├── hosts.ini
│   └── group_vars/all.yml
├── playbooks/
│   ├── prepare.yml      # common + docker + frappe roles
│   ├── deploy.yml       # services role
│   └── site.yml         # runs prepare.yml then deploy.yml
└── roles/
    ├── common/          # apt cache update and base packages
    ├── docker/          # install Docker, enable service, add user to docker group
    ├── frappe/          # app directory, compose file, init.sh, config files
    └── services/        # start the containers with Docker Compose
```

## Variables

All variables are in `inventory/group_vars/all.yml`:

- `app_user`: user that owns the app files (`ubuntu`)
- `app_dir`: application directory on the target (`/opt/frappe-crm`)
- `app_port`: port the app is served on (`8000`)
- `restart_policy`: container restart policy (`unless-stopped`)
- `common_packages`: base packages to install
- `docker_packages`: Docker packages to install
- `frappe_branch`: branch of `frappe/crm` used to download the compose file and `init.sh` (`develop`)

## Prerequisites

1. Two Ubuntu servers (control and target) that can reach each other over SSH.
2. Ansible on the control node:
   ```bash
   sudo apt update
   sudo apt install -y software-properties-common
   sudo add-apt-repository --yes --update ppa:ansible/ansible
   sudo apt install -y ansible
   ```
   The full `ansible` package includes the `community.docker` collection used by the `services` role.
3. SSH key access from the control node to the target:
   ```bash
   ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
   cat ~/.ssh/id_ed25519.pub     # add this line to ~/.ssh/authorized_keys on the target
   ```
   `ansible.cfg` expects the key at `~/.ssh/id_ed25519`.
4. Target security group: allow SSH (22) and the app port (8000), restricted to your own IP.

## How to run

1. Edit `inventory/hosts.ini` and replace the placeholder with the target's private IP.
2. Check the connection:
   ```bash
   ansible all -m ping
   ```
3. Run everything:
   ```bash
   ansible-playbook playbooks/site.yml
   ```
   Or run the parts separately:
   ```bash
   ansible-playbook playbooks/prepare.yml
   ansible-playbook playbooks/deploy.yml
   ```
4. The first start takes several minutes, because the container sets up Frappe and installs the CRM app. Check progress with:
   ```bash
   ansible all -b -m shell -a "docker logs --tail 20 crm-frappe-1"
   ```
5. Open `http://<target-public-ip>:8000/crm` and log in with `Administrator` / `admin`.

## Idempotency

Run `ansible-playbook playbooks/site.yml` a second time. Every task reports `ok` and the recap shows `changed=0`. See the screenshots folder.

## Notes

- **SSL is disabled.** The app is served over plain HTTP on port 8000. The Frappe container's database client required SSL, but the MariaDB server in the compose file does not support it, so site creation failed (`ERROR 2026: TLS/SSL error: SSL is required, but the server does not support it`). The `frappe` role writes a small client config (`skip-ssl`) and mounts it into the container through `docker-compose.override.yml`.
- **Docker comes from Ubuntu's packages** (`docker.io` and `docker-compose-v2`). On Ubuntu 26.04, `docker-ce` had no installable candidate from Docker's apt repository at the time of testing.
- **Upstream files:** `docker-compose.yml` and `init.sh` are downloaded from the `frappe/crm` repository (branch set by `frappe_branch`). They are only downloaded if they do not already exist. Compose may print a warning that the `version` attribute is obsolete; it comes from the upstream file and is harmless.
- **Demo only:** the upstream setup uses default credentials (`admin` for the app, `123` for the MariaDB root password). The security group limits access to a single IP. This is not production-ready.

## Demo

- Loom video: ADD_LOOM_LINK
- Screenshots are in the `screenshots/` folder.