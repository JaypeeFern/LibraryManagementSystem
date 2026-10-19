# Docker deployment

The production workflow builds the Django image in GitHub Actions, publishes it
to GHCR under the full commit SHA, records its content digest, verifies that
digest, then updates Coolify's `IMAGE_REFERENCE` and triggers deployment.
Production Compose pulls by digest, so registry tag changes cannot change the
deployed image. `latest` is published for registry convenience and is never
used for deployment.

## Coolify setup

1. Create a Docker Compose resource for this repository and point it at the
   root `docker-compose.yml`.
2. Turn off Coolify's automatic Git deployment. The workflow triggers Coolify
   only after the full-SHA image is present and verified.
3. Make the GHCR package readable by Coolify. For a private package, add a
   GitHub token with `read:packages` as the Coolify build variable `GHCR_TOKEN`
   and use this custom build command:

   ```sh
   sh -c '
     set -eu
     umask 077
     DOCKER_CONFIG=$(mktemp -d)
     export DOCKER_CONFIG
     trap '\''rm -rf "$DOCKER_CONFIG"'\'' EXIT
     trap '\''exit 1'\'' HUP INT TERM
     GHCR_TOKEN=$(grep "^GHCR_TOKEN=" /artifacts/build-time.env | cut -d= -f2- | sed -e "s/^\"//" -e "s/\"$//")
     printf "%s" "$GHCR_TOKEN" | docker login ghcr.io -u JaypeeFern --password-stdin
     unset GHCR_TOKEN
     docker compose -f docker-compose.yml pull
   '
   ```

   The temporary Docker config is private to this pull and is removed when the
   command exits, including when login or pulling fails. This prevents the
   registry credential from remaining in the persistent host user's default
   `~/.docker/config.json`.

4. Set the runtime variables `SECRET_KEY`, `ALLOWED_HOSTS`, and
   `CSRF_TRUSTED_ORIGINS`. `ALLOWED_HOSTS` is a comma-separated hostname list;
   `CSRF_TRUSTED_ORIGINS` is a comma-separated origin list including `https://`.
5. Set `APP_DATA_PATH` to a persistent host directory. It defaults to
   `/data/coolify/persistent/librarymanagementsystem` and stores both SQLite
   and uploaded media. Ensure the directory is writable by container UID
   `10001` before the first deploy.
6. Add these repository secrets if CI should trigger production deployment:
   `COOLIFY_WEBHOOK_URL`, `COOLIFY_TOKEN`, and `COOLIFY_API_TOKEN`. If all are
   absent, CI builds and verifies the image but skips automatic deployment; a
   partial set fails the workflow.

## Django signing-key rotation

The key previously present in public Git history must be treated as
compromised, even after history cleanup. The repository's configured
deployment uses Coolify; confirm the actual production resource and account
before making changes, since the connected Coolify team may not own it. Rotate
the production `SECRET_KEY` through the owning platform's protected
runtime-variable interface. Do not put either key in this repository, a
ticket, shell history, logs, or a chat message.

1. Identify the production app, owning platform/account, ingress, and current
   runtime-variable source. Schedule a short maintenance window and confirm
   the current deployment is healthy. Record the currently deployed
   `IMAGE_REFERENCE` digest for troubleshooting. Do not read or copy the
   current key into notes.
2. Generate a new high-entropy Django secret using a trusted local secret
   manager or secret-generation facility. Keep the value out of terminal output
   and store it only in the platform's protected `SECRET_KEY` variable.
3. Save the new variable and redeploy the same verified image digest. The
   application requires `SECRET_KEY` at startup, so a missing value will fail
   closed rather than use a fallback.
4. Check the deployment health state and HTTPS login, logout, and a
   staff-authorized action. Watch application logs for startup/configuration
   errors without logging environment values. Confirm a fresh login works.
5. Tell users to sign in again. Rotation invalidates existing sessions and
   other Django signatures created with the old key, including outstanding
   password-reset links and signed-cookie data.
6. If the deployment fails, redeploy the recorded verified image digest with
   a newly generated key. Do not restore the historically exposed key as a
   rollback value. Record completion time and the new key's secret-manager
   version, never the key itself.
7. A force-push removes the exposed commit from reachable repository refs but
   does not necessarily remove GitHub's cached commit views or copies in
   forks. After confirming all refs are clean and rotating or revoking every
   exposed credential, request cached-view removal through
   [GitHub Support's sensitive-data process](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
   when exposed data remains sensitive and its risk is not already mitigated
   by credential rotation. Verify old commit URLs no longer expose the data;
   do not treat a successful force-push as proof that GitHub's caches were
   purged.

The webhook must be an HTTPS resource deploy URL in the form
`https://<coolify-host>/api/v1/deploy?uuid=<application-uuid>&force=false`.
The API token must be allowed to read and update the application's source
commit and `IMAGE_REFERENCE` environment variable. The workflow creates that
variable if missing, verifies the saved digest, and only then triggers deploy.

## Local Docker use

Copy `.env.example` to `.env`, set a local secret and host values, then select
the current full Git SHA and local data directory before composing:

```powershell
Copy-Item .env.example .env
$env:IMAGE_REFERENCE = "library-management-system:local"
$env:APP_DATA_PATH = "./.compose-data"
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
```

The local build override enables Django debug mode for local-only HTTP use.
Open `http://127.0.0.1:8000` after the service reports healthy.

For a POSIX shell:

```sh
cp .env.example .env
export IMAGE_REFERENCE="library-management-system:local"
export APP_DATA_PATH="./.compose-data"
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
```

The Compose override adds a build context only for local use. Production
Coolify uses `docker-compose.yml` alone. CI writes a digest reference such as
`ghcr.io/jaypeefern/library-management-system@sha256:<64-hex-digest>` to its
`IMAGE_REFERENCE` environment variable before deployment. For a manual deploy,
set that variable to a previously verified digest reference. Do not deploy by
tag.

SQLite databases are runtime data and must not be committed to Git. They are
excluded from Docker images. Before moving an existing deployment to Docker,
back up its database and uploaded media, then place them in `APP_DATA_PATH` as
`db.sqlite3` and `media/` before starting the new image. A fresh deployment
creates the schema through the container's migration step.

## Image pipeline

`.github/workflows/build-image.yml` builds on changes to app code, templates,
static assets, requirements, or Docker configuration on `main`. It publishes
`ghcr.io/jaypeefern/library-management-system:<full-git-sha>` and a convenience
`latest` tag, emits build provenance, verifies the exact image digest, and only
then starts the optional Coolify deployment step. The same digest is saved as
`IMAGE_REFERENCE` in Coolify and used by Compose. Pull requests run the image
build without publishing or deploying it.
