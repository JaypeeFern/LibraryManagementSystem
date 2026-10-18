# Docker deployment

The production workflow builds the Django image in GitHub Actions, publishes it
to GHCR under the full commit SHA, confirms the image exists, then pins and
triggers the Coolify deployment. Production Compose only pulls that immutable
tag; `latest` is published for registry convenience and is never used for
deployment.

## Coolify setup

1. Create a Docker Compose resource for this repository and point it at the
   root `docker-compose.yml`.
2. Turn off Coolify's automatic Git deployment. The workflow triggers Coolify
   only after the full-SHA image is present and verified.
3. Make the GHCR package readable by Coolify. For a private package, add a
   GitHub token with `read:packages` as the Coolify build variable `GHCR_TOKEN`
   and use this custom build command:

   ```sh
   sh -c 'T=$(grep "^GHCR_TOKEN=" /artifacts/build-time.env | cut -d= -f2- | sed -e "s/^\"//" -e "s/\"$//"); echo "$T" | docker login ghcr.io -u JaypeeFern --password-stdin && docker compose -f docker-compose.yml pull'
   ```

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

The webhook must be an HTTPS resource deploy URL in the form
`https://<coolify-host>/api/v1/deploy?uuid=<application-uuid>&force=false`.
The API token must be allowed to read and update the application's source
commit.

## Local Docker use

Copy `.env.example` to `.env`, set a local secret and host values, then select
the current full Git SHA and local data directory before composing:

```powershell
Copy-Item .env.example .env
$env:SOURCE_COMMIT = (git rev-parse --verify HEAD).Trim()
$env:APP_DATA_PATH = "./.compose-data"
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
```

The local build override enables Django debug mode for local-only HTTP use.
Open `http://127.0.0.1:8000` after the service reports healthy.

For a POSIX shell:

```sh
cp .env.example .env
export SOURCE_COMMIT="$(git rev-parse --verify HEAD)"
export APP_DATA_PATH="./.compose-data"
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
```

The Compose override adds a build context only for local use. Production
Coolify uses `docker-compose.yml` alone and must have `SOURCE_COMMIT` available
for Compose interpolation. Do not define a separate container runtime
environment variable named `SOURCE_COMMIT`.

SQLite databases are runtime data and must not be committed to Git. They are
excluded from Docker images. Before moving an existing deployment to Docker,
back up its database and uploaded media, then place them in `APP_DATA_PATH` as
`db.sqlite3` and `media/` before starting the new image. A fresh deployment
creates the schema through the container's migration step.

## Image pipeline

`.github/workflows/build-image.yml` builds on changes to app code, templates,
static assets, requirements, or Docker configuration on `main`. It publishes
`ghcr.io/jaypeefern/library-management-system:<full-git-sha>` and a convenience
`latest` tag, verifies the immutable tag, and only then starts the optional
Coolify deployment step. Coolify's built-in source revision supplies the
`SOURCE_COMMIT` Compose value; that value selects the image and is not passed to
the Django process.
