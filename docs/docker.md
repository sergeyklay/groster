# Running groster with Docker

You can run groster in Docker instead of installing Python locally. This is the recommended approach for production deployments.

## Prerequisites

- Docker 23.0+ (BuildKit enabled by default)
- Docker Compose v2

## Quick start

Copy the example environment file and fill in your credentials:

```shell
cp .env.example .env
# Edit .env with your Blizzard API and Discord credentials
```

Start the Discord bot:

```shell
docker compose up -d
```

## Running CLI commands

Run a roster update (one-shot, shares the same data volume):

```shell
docker compose run --rm bot update --region eu --realm terokkar --guild darq-side-of-the-moon
```

Check the version:

```shell
docker compose run --rm bot --version
```

## Environment variables

See [.env.example](../.env.example) for the full list of supported variables. Secrets go in `.env` (gitignored) and are never baked into the image.

## Volume management

The `groster-data` volume persists all CSV data and character profiles at `/app/data` inside the container.

Back up volume data:

```shell
docker run --rm -v groster_groster-data:/data -v "$(pwd)":/backup busybox \
    tar czf /backup/groster-data-backup.tar.gz -C /data .
```

Restore from backup:

```shell
docker run --rm -v groster_groster-data:/data -v "$(pwd)":/backup busybox \
    tar xzf /backup/groster-data-backup.tar.gz -C /data
```

## Scheduled updates

Add a crontab entry to run roster updates automatically:

```crontab
0 4 * * * cd /path/to/guild-roster && docker compose run --rm bot update >> /var/log/groster-update.log 2>&1
```

## Viewing logs

```shell
docker compose logs -f bot
```

## Rebuilding after code changes

```shell
docker compose build && docker compose up -d
```
