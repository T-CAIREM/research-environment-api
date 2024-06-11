# Research Environment API

## Bootstrapping a Cloud SQL database

### Permissions

In order for the app's user to have access to the newly created database, the following permissions need to be present:
```GRANT ALL ON SCHEMA public TO username```

# Credentials

HDN is using sops to manage credentials internally in the project

### Prerequisites

Install sops:

```commandline
brew install sops
```

Establish connection with GCP as sops are using GCP Cloud Key Management to ensure security of encryption key.

### Credentials Management

To decrypt credentials in directory `./credentials/dev` or `./credentials/prod` use

```commandline
sops --decrypt credentials.enc.json > credentials.json
```

To update credentials decrypt them using above command, change or add new value in `credentials.json` file, and encrypt using:

```commandline
sops --encrypt credentials.json > credentials.enc.json
```

*REMEMBER THAT ONLY ENCRYPTED FILE NEEDS TO BE PUSHED TO REMOTE REPOSITORY*

