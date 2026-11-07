# Frappe CRM -- Task 1: Project Exploration

## Project overview

This repository documents the local setup, exploration, and
troubleshooting completed for **Task 1 of the PearlThoughts DevOps
Internship**.

[Frappe CRM](https://github.com/frappe/crm) is a customer relationship
management application built on the Frappe Framework. A CRM helps a
business organize customer information and manage the sales process,
from an initial prospect through follow-up and deal tracking.

The application was run locally on Windows using Docker Compose. The
verified local URL was:

`http://crm-task1.localhost:8000`

## Task objectives

-   Clone and explore the Frappe CRM internship repository.
-   Run the application locally using Docker.
-   Understand the project structure and the role of its main
    technologies.
-   Explore the CRM's customer and sales-related modules.
-   Investigate setup issues and document the troubleshooting steps.
-   Prepare project documentation and a walkthrough for submission.

## What is a CRM?

A Customer Relationship Management (CRM) system provides a central place
to manage information about prospective and existing customers. It helps
teams keep customer records organized, track sales opportunities, and
maintain visibility into follow-up activities.

In this project, Frappe CRM provides the application layer, while the
Frappe Framework supplies the underlying site, DocType, and application
infrastructure.

## CRM application areas explored

The following are the main CRM areas identified during project
exploration. The descriptions explain their general purpose; use the
running application to confirm the exact fields, actions, and workflow
available in this repository version.

  -----------------------------------------------------------------------
  CRM area                Purpose                 How it fits into a
                                                  sales workflow
  ----------------------- ----------------------- -----------------------
  **Leads**               Records prospective     A sales team can
                          customers or people who capture a prospect and
                          have shown initial      keep the initial
                          interest.               customer information in
                                                  one place.

  **Contacts**            Stores information      A contact can represent
                          about individual        a person with whom the
                          people.                 business communicates.

  **Organizations**       Stores company or       Helps associate people
                          organization records.   and sales opportunities
                                                  with the relevant
                                                  business.

  **Deals**               Tracks potential sales  Helps the team follow
                          opportunities.          an opportunity as it
                                                  progresses through the
                                                  sales process.
  -----------------------------------------------------------------------

### Example CRM workflow

1.  **Capture a lead:** Record a prospective customer and the available
    details.
2.  **Review the prospect:** Understand the customer's interest and
    determine the appropriate next step.
3.  **Maintain contact information:** Keep the relevant person's details
    organized.
4.  **Associate an organization:** Link the person or opportunity to a
    company where applicable.
5.  **Track a deal:** Record and monitor a sales opportunity as it
    progresses.
6.  **Follow up:** Keep the customer conversation and next steps
    organized in the CRM.

This is a conceptual workflow to explain how the CRM areas relate; it is
not a claim that every step was independently tested in the local
application.

## Technologies used

  -----------------------------------------------------------------------
  Technology                          Role in this project
  ----------------------------------- -----------------------------------
  **Frappe Framework**                Framework on which the site and
                                      application run. A Frappe site has
                                      site configuration and a database
                                      and is initialized using Bench
                                      commands.

  **Frappe CRM**                      CRM application installed on the
                                      Frappe site. Installing the app
                                      adds its CRM functionality and
                                      DocTypes to the site.

  **Docker**                          Runs the application and supporting
                                      services in isolated containers.

  **Docker Compose**                  Defines and runs the related
                                      containers together using a YAML
                                      configuration.

  **MariaDB**                         Relational database used by the
                                      Frappe site. Site initialization
                                      creates the database schema and
                                      tables.

  **Redis**                           Supporting service used by the
                                      local Frappe environment.
  -----------------------------------------------------------------------

## Local setup and service architecture

The project was run locally using Docker Compose. The Compose
configuration used was:

`docker/docker-compose.yml`

  Container         Purpose
  ----------------- -----------------------------------------------
  `crm-frappe-1`    Runs Frappe Bench and the Frappe application.
  `crm-mariadb-1`   Provides the MariaDB database service.
  `crm-redis-1`     Provides the Redis supporting service.

### High-level architecture

``` text
                  Browser
                     |
                     | http://crm-task1.localhost:8000
                     v
          Frappe application / Bench
              /                 \
             v                   v
       MariaDB container    Redis container
       Application data     Cache / queue /
                            Socket.IO support

       Docker Compose provides the service network
```

A browser request reaches the Frappe application. Frappe communicates
with MariaDB for persistent database operations and Redis for the
configured supporting functions. Docker Compose provides the internal
service network.

## Project structure explored

  -----------------------------------------------------------------------------
  Folder or file                Purpose                 Status
  ----------------------------- ----------------------- -----------------------
  `docker/`                     Contains Docker-related Verified
                                configuration used by
                                the local environment.

  `docker/docker-compose.yml`   Defines the Docker      Verified
                                Compose services and
                                configuration.

  `docker/init.sh`              Shell script used       Verified
                                during environment
                                initialization.

  `docker/recovery-backup/`     Directory containing    Verified
                                recovery or
                                backup-related
                                resources.
  -----------------------------------------------------------------------------

## Site installation and verification

A Frappe site named `crm-task1.localhost` was created and the CRM app
was installed.

The successful installation output included:

-   Frappe installation.
-   CRM installation.
-   DocType updates.
-   CRM custom-field setup.
-   Setting `crm-task1.localhost` as the current site.

The site was verified by opening `http://crm-task1.localhost:8000` in a
browser. The application loaded successfully after the Frappe container
was restarted.

Passwords and other credentials are intentionally excluded from this
README.

## Troubleshooting and resolutions

### 1. MariaDB client SSL connection error

**Observed error:**

``` text
ERROR 2026 (HY000): TLS/SSL error: SSL is required, but the server does not support it.
```

Investigation showed that the MariaDB server reported
`have_ssl=DISABLED` and `require_secure_transport=OFF`. A direct client
connection using `--skip-ssl` succeeded. This indicated that the local
MariaDB client was attempting an SSL connection even though SSL was
disabled on the local server.

A temporary client configuration was created inside the running Frappe
container as root:

``` bash
docker exec -u 0 crm-frappe-1 sh -c "printf '[client]\nskip-ssl\n' > /etc/mysql/conf.d/zz-local-no-ssl.cnf"
```

The client defaults were checked with:

``` bash
docker exec crm-frappe-1 bash -lc "mysql --print-defaults"
```

The output included `--skip-ssl`, and a database connection test
succeeded.

**Important:** This was a local-development workaround. The
configuration was created inside the running container's writable layer
and may not survive container recreation. Disabling SSL is not a
production solution; production database connections should use
correctly configured TLS.

### 2. Original site database was incomplete

The original site `crm.localhost` referenced database
`_c8b3e5206096f0bd`. That database was found to contain zero tables.
This showed that the existence of a site directory alone did not prove
that the site database schema had been initialized successfully.

A separate site named `crm-task1.localhost` was installed using database
`_3dfa23c5af3c2958`. The new database was verified to contain **291
tables**. The count was checked through MariaDB's
`INFORMATION_SCHEMA.TABLES`.

The site installation command used in the local environment was:

``` bash
docker exec crm-frappe-1 bash -lc "cd /home/frappe/frappe-bench && bench new-site crm-task1.localhost --force --db-name _3dfa23c5af3c2958 --mariadb-root-password '<DB_ROOT_PASSWORD>' --admin-password '<SITE_ADMIN_PASSWORD>' --mariadb-user-host-login-scope='%' --install-app crm --set-default"
```

Replace the placeholders with the appropriate local credentials when
running the command. Do not commit real passwords to GitHub.

### 3. Browser displayed a missing `tabSingles` table

The browser initially displayed a database error indicating that table
`tabSingles` did not exist in the original database. Investigation
showed that the browser request was still being handled by a Frappe
process using the old/incomplete site database, while the newly
installed site database contained the expected tables.

The Frappe container was restarted:

``` bash
docker restart crm-frappe-1
```

After the restart, the application loaded successfully at
`http://crm-task1.localhost:8000`.

### 4. Scheduler disabled message

The successful installation output included:

``` text
*** Scheduler is disabled ***
```

In this environment, the message did not prevent the site from loading
in the browser and was not the cause of the missing-database-table
error.

## Useful commands

  -----------------------------------------------------------------------------
  Command                                   Purpose
  ----------------------------------------- -----------------------------------
  `docker ps`                               Lists running containers.

  `docker restart crm-frappe-1`             Restarts the Frappe container.

  `docker exec crm-frappe-1 ...`            Runs a command inside the Frappe
                                            container.

  `docker exec -u 0 crm-frappe-1 ...`       Runs a command as root inside the
                                            Frappe container.

  `mysql --print-defaults`                  Displays the client options loaded
                                            from configuration.

  `mysql --skip-ssl ...`                    Tests a local database connection
                                            without client SSL.

  `bench new-site ...`                      Creates and initializes a Frappe
                                            site.

  MariaDB `INFORMATION_SCHEMA.TABLES` query Checks the number of tables in a
                                            selected site database.

  `docker exec crm-mariadb-1 mariadb ...`   Runs the MariaDB client inside the
                                            database container for database
                                            inspection.
  -----------------------------------------------------------------------------

## Key learnings

-   Docker Compose coordinates the Frappe application and its supporting
    services.
-   Frappe site initialization creates the database schema and installs
    the selected application.
-   A site folder can exist even when its database has not been
    initialized successfully.
-   MariaDB client SSL settings must be compatible with the server
    configuration.
-   Database table counts, checked through `INFORMATION_SCHEMA.TABLES`,
    can help verify whether site initialization completed.
-   The original database had zero tables, whereas the newly initialized
    site database had 291 tables. This comparison helped identify which
    site database was ready for use.
-   Restarting the application container can reload configuration and
    running web processes.
-   Changes made only inside a running container may be lost when that
    container is recreated.
-   A CRM organizes customer information and sales opportunities in
    related records such as leads, contacts, organizations, and deals.

## Conclusion

Frappe CRM was successfully installed and accessed locally using Docker.
The main troubleshooting work involved resolving the local MariaDB
client SSL mismatch, identifying that the original site database was
empty, installing a separate initialized site, verifying its database
tables, and restarting the Frappe container to resolve the browser
error.

This task provided practical exposure to Docker Compose, containerized
application setup, Frappe Bench, database initialization, Redis, CRM
concepts, and systematic troubleshooting.

------------------------------------------------------------------------

**Project:** PearlThoughts DevOps Internship -- Task 1\
**Repository:**
[frappe-crm-devops-internship](https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship)\
**Local application URL:** `http://crm-task1.localhost:8000`
