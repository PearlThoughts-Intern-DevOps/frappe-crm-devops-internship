Task 1: Frappe CRM – Project Exploration Report

Internship: DevOps Internship – PearlThoughts
Student: SAHIL SHAIKH
Project: Frappe CRM
Task: Task 1 – Explore Frappe CRM

⸻

1. Introduction

Frappe CRM is an open-source Customer Relationship Management (CRM) application built using the Frappe Framework. It helps organizations manage customer information, sales activities, leads, deals and business relationships through a centralized platform.

The objective of this task is to explore the Frappe CRM project, understand its architecture, identify the technologies used and examine how the application operates locally.

2. Objectives

* Understand the purpose and functionality of Frappe CRM.
* Explore the project repository and folder structure.
* Identify the major technologies and frameworks.
* Understand the application’s architecture and workflow.
* Run and explore the application locally.
* Understand the DevOps concepts involved in the project.

3. Overview of Frappe CRM

Frappe CRM is designed to simplify customer relationship management and sales processes.

Its major functionalities include:

* Lead management
* Contact management
* Deal management
* Sales pipeline management
* Task management
* Customer communication
* Sales activity tracking

4. Technologies Used

The following technologies are relevant to the Frappe CRM ecosystem. Their actual use in the repository should be verified during exploration.

Technology	Purpose
Python	Backend development
JavaScript	Frontend functionality
Vue.js	User interface
Frappe Framework	Application framework
MariaDB	Relational database
Redis	Caching and background jobs
Docker	Containerization
Git	Version control

5. Project Folder Structure

This section explains the important folders and configuration files explored in the repository.

The repository contains different folders that organize the application’s source code, frontend, configuration and supporting resources\.

### Important Directories

|Folder     |Purpose                                                              |
|-----------|---------------------------------------------------------------------|
|`crm/`     |Contains the CRM application’s backend and application-related files.|
|`frontend/`|Contains frontend source code and user interface components.         |
|`docker/`  |Contains Docker-related configuration and deployment resources.      |
|`docs/`    |Contains project documentation.                                      
|`.github/` |Contains GitHub-related configuration and workflows.                 |

### Other Important Files

- `README.md` – Provides project information and setup instructions\.
- `package.json` – Contains frontend dependencies and scripts\.
- `pyproject.toml` – Contains Python project configuration and dependencies\.

Exploring these directories helps understand how the application is organized and how its different components work together\.
Detailed Exploration of the crm/ Directory

The crm/ directory contains the main Frappe CRM application package. It organizes backend functionality, business logic, configuration, integrations, permissions, templates and supporting resources.

Important Subdirectories

* api/: Backend API functionality.
* automation/: Automation-related functionality.
* config/: Application configuration.
* demo/: Demonstration resources and sample data.
* domain_enrichment/: Domain enrichment functionality.
* extends/: Framework extension functionality.
* fcrm/: Core CRM modules.
* integrations/: External service integrations.
* lead_syncing/: Lead synchronization functionality.
* locale/: Localization and translation resources.
* overrides/: Framework or application overrides.
* patches/: Application update patches.
* permissions/: Permission-related configurations.
* public/: Public assets.
* templates/: Reusable templates.
* tests/: Automated test files.
* utils/: Utility functions.
* www/: Website pages and routes.

Important Python and Configuration Files

* __init__.py: Defines the Python package.
* activation.py: Activation-related functionality.
* hooks.py: Defines integration points with the Frappe Framework.
* install.py: Installation-related functionality.
* uninstall.py: Uninstallation-related functionality.
* modules.txt: Lists application modules.
* patches.txt: Lists application patches.
* telemetry.py: Telemetry-related functionality.
* crowdin.yml: Translation management configuration.

This directory demonstrates how a Frappe application separates its business functionality, configuration, integrations and supporting components into organized modules.

### 5.1 Root Directory Structure

The repository contains several important directories and configuration files.

- crm/ – Contains the Frappe CRM application.
- docker/ – Contains Docker-related configuration files.
- docs/ – Contains project documentation.
- frappe-ui/ – Contains frontend-related project resources.
- frontend/ – Contains frontend-related resources.
- scripts/ – Contains utility and automation scripts.
- .github/ – Contains GitHub-related configuration and workflows.
- .devcontainer/ – Contains development container configuration.
- .vscode/ – Contains Visual Studio Code configuration.

### 5.2 CRM Directory

The crm/ directory contains the main CRM application package.

The folders observed include:

- api/
- automation/
- config/
- demo/
- domain_enrichment/
- extends/
- fcrm/
- integrations/
- lead_syncing/
- locale/
- overrides/
- patches/
- permissions/
- public/
- templates/
- tests/
- utils/
- www/

It also contains Python and configuration files such as hooks.py, install.py, uninstall.py, modules.txt and patches.txt.

### 5.3 CRM API Directory

The crm/api/ directory contains Python files related to API functionality.

Some observed files include:

- activities.py
- assignment_rule.py
- auth.py
- availability.py
- comment.py
- contact.py
- dashboard.py
- notifications.py
- onboarding.py
- settings.py
- todo.py
- user.py
- views.py
- whatsapp.py

These filenames suggest that the directory organizes backend operations related to CRM features. Their exact functionality can be confirmed by inspecting the source code.

### 5.4 FCRM Directory

The crm/fcrm/ directory contains:

- doctype/
- workspace/
- frappe_crm.json
- __init__.py

The doctype/ directory is used for Frappe DocType definitions, while workspace/ contains workspace-related resources. The exact contents will be examined further.

6. Application Architecture

The application follows a client-server architecture.

The frontend provides the user interface, while the backend handles business logic and communication with the database.

Supporting services such as Redis and background workers help manage caching and asynchronous operations.

7. Local Installation and Execution

Operating System: WINDOWS 11

Installation Method: DOCKER DESKTOP

Application URL: [Enter your local URL]

Execution Result: [Describe whether the application started successfully.]

8. Application Exploration

The application was explored to understand its dashboard, navigation, leads, contacts, deals and other available CRM features.

(Add actual screenshots and explanations here.)

9. DevOps Concepts

The project provides an opportunity to understand several DevOps concepts:

* Git-based version control
* Docker-based containerization
* Environment configuration
* Application setup and deployment
* Service management

10. Challenges Faced

(Add actual installation issues, errors and their solutions.)

11. Key Learnings

Through this task, I learned about the structure of an open-source CRM application, its technology ecosystem, the role of different application components and the importance of version control and containerization in DevOps.

12. Conclusion

This project exploration provided an introduction to Frappe CRM and its underlying technologies. It helped develop an understanding of how a modern CRM application is structured and how DevOps practices support application setup and deployment.
