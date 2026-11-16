# Ansible Automation for Frappe CRM

Ansible project that prepares a machine and starts the Frappe CRM Docker stack with one command.
Target is the local machine (`localhost`), so no SSH keys or IP addresses are needed.

## What it does

| Role | What it automates |
|------|-------------------|
| `common` | Updates apt cache and installs base packages (curl, git, gnupg, ca-certificates) |
| `docker` | Checks if Docker is installed (installs it only if missing), makes sure the service is running, verifies `docker compose`, adds the user to the `docker` group |
| `frappe_crm` | Verifies the compose project folder and file exist, makes the init script executable, starts the CRM containers with `docker compose` |

All tasks are idempotent: a second run reports `changed=0`.

## Project layout

```
ansible.cfg                    # Ansible settings (inventory path, roles path, sudo)
site.yml                       # Main playbook: runs the three roles in order
inventory/
  hosts.ini                    # Inventory: localhost
  group_vars/all.yml           # Variables you edit (compose folder, file names)
roles/
  common/   {tasks,defaults}/main.yml
  docker/   {tasks,defaults}/main.yml
  frappe_crm/ {tasks,defaults}/main.yml
```

## Variables (`inventory/group_vars/all.yml`)

| Variable | Meaning |
|----------|---------|
| `crm_project_dir` | Absolute path of the folder containing the docker-compose file |
| `crm_compose_file` | Compose file name (default `docker-compose.yml`) |
| `crm_init_file` | Optional init script inside that folder (made executable) |

## Requirements

Ubuntu/Debian or WSL2 Ubuntu, Docker, and sudo access.

## Run

```bash
# 1. Install Ansible
sudo apt update && sudo apt install -y pipx
pipx install --include-deps ansible
pipx ensurepath            # reopen the terminal afterwards

# 2. Set your compose folder
nano inventory/group_vars/all.yml

# 3. Test the connection and syntax
ansible crm_servers -m ping
ansible-playbook site.yml --syntax-check

# 4. First run (use -K if sudo asks for a password)
ansible-playbook site.yml

# 5. Second run: must show changed=0 (proves idempotency)
ansible-playbook site.yml
```

Run one role only: `ansible-playbook site.yml --tags docker`

Check the containers:

```bash
docker compose -f <crm_project_dir>/docker-compose.yml ps
docker compose -f <crm_project_dir>/docker-compose.yml logs -f frappe
```

The first CRM start takes several minutes while Frappe is installed. Then open http://localhost:8000.

## Troubleshooting

- **"No inventory was parsed"**: run commands from the project folder, and keep it in the Linux
  home (not `/mnt/c`), otherwise Ansible ignores `ansible.cfg`.
- **sudo "Timed out waiting for become"**: use passwordless sudo for the user, or run with `-K`.
- **Container fails with "Network is unreachable" when downloading packages**: IPv6 is broken
  in WSL/Docker. Fix with
  `sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 && sudo service docker restart`,
  then `docker compose down -v` in the compose folder and run the playbook again.
