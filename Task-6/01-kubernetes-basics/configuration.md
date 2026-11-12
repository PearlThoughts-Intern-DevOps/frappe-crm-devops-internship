# Kubernetes ConfigMaps and Secrets

## ConfigMaps

ConfigMaps store non-sensitive configuration separately from container images.

Examples:
- Application environment settings.
- Service hostnames.
- Configuration parameters.

Example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: development
  DB_HOST: mariadb
```

## Secrets

Secrets store sensitive configuration such as passwords and tokens.

Example structure:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
stringData:
  DB_PASSWORD: replace-with-your-password
```

Never commit real credentials to GitHub.

Kubernetes Secret values are base64-encoded by default, not automatically encrypted. Cluster encryption and access controls should be configured for stronger protection.

## ConfigMaps vs Secrets

| ConfigMap | Secret |
|---|---|
| Non-sensitive configuration | Sensitive configuration |
| Plain-text values | Base64-encoded values by default |
| Can be mounted or exposed as environment variables | Can be mounted or exposed as environment variables |