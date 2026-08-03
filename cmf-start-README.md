# CMF Server Launcher — `cmf-start.sh`

A user-friendly script that starts the CMF server stack quietly and tells you
when each service is accessible, instead of flooding the terminal with raw
Docker Compose logs.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker + Docker Compose | Docker daemon must be running |
| `curl` | Used to check service health |
| `.env` file | Must exist in the `cmf/` directory (see below) |

---

## Step 1 — Create your `.env` file

Copy the example and fill in your values:

```bash
cp env-example .env
```

**Key parameters you must set:**

```env
# URL that the browser uses to reach the CMF API (replace with your server IP)
REACT_APP_CMF_API_URL=http://<your-server-ip>:80

# Nginx ports
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_PORT=5432
POSTGRES_DB=mlmd

# Data storage directory
CMF_DATA_DIR=~/cmf_data

# MCP server port
MCP_PORT=8382
```

---

## Step 2 — Run the script from the `cmf/` directory

```bash
cd /path/to/cmf
sh ./cmf-start.sh
```

Or with execute permission:

```bash
chmod +x cmf-start.sh
./cmf-start.sh
```

The script will:
1. Check that Docker is running and `.env` exists
2. Ask you to confirm `.env` is configured correctly
3. Build and start all Docker containers (quietly)
4. Wait for each service to become ready
5. Print a summary box with the accessible URLs

---

## Options

| Flag | Description |
|---|---|
| *(none)* | Default — builds images if needed, then starts |
| `--no-build` | Skip rebuilding images (faster if nothing changed) |
| `--help` | Show usage |

```bash
sh ./cmf-start.sh --no-build
```

---

## What services are started?

| Service | Description | Accessible at |
|---|---|---|
| CMF Server | FastAPI backend | `http://<ip>:<NGINX_HTTP_PORT>/api/` |
| CMF UI | React frontend | `http://<ip>:<NGINX_HTTP_PORT>` |
| MCP Server | Model Context Protocol server | `http://<ip>:<MCP_PORT>/mcp` |
| PostgreSQL | Database (internal only) | — |
| Nginx | Reverse proxy (routes UI + API) | port 80 / 443 |
| TensorBoard | Metrics viewer (internal) | via UI |

---

## Stopping all services

```bash
docker compose -f docker-compose-server.yml down
```

---

## Troubleshooting

**CMF Server did not respond**
```bash
docker compose -f docker-compose-server.yml logs server
```

**UI did not respond**
```bash
docker compose -f docker-compose-server.yml logs ui
```

**MCP did not respond**
```bash
docker compose -f docker-compose-server.yml logs mcp
```

**See status of all containers**
```bash
docker compose -f docker-compose-server.yml ps
```

**502 Bad Gateway from nginx**
Nginx is up but the backend (`cmf-server`) hasn't finished starting yet.
Wait a few seconds and refresh, or check `logs server`.

---

## Notes

- The script must be run **from inside the `cmf/` directory** — it looks for
  `docker-compose-server.yml` in the current working directory.
- On the **first run**, Docker builds all images which can take several minutes.
  Subsequent runs with `--no-build` are much faster.
- The default service wait timeout is **300 seconds**. Override it for slower
  machines:
  ```bash
  SERVICE_WAIT_TIMEOUT=300 sh ./cmf-start.sh
  ```
- If the **CMF Server fails** to start, the UI and MCP checks are automatically
  skipped since they depend on the server being healthy.
