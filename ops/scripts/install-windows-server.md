# Windows Server Install

1. Install Docker Desktop or Docker Engine for Windows with Linux containers enabled.
2. Clone or copy the repository to a stable path such as `D:\plastic-engineering-data-hub`.
3. Copy `.env.example` to `.env` and replace all placeholder values.
4. Place IT-provided certificate and key files in `ops\caddy\certs\` and set `CADDY_TLS_DIRECTIVE` to those mounted paths.
5. Start PowerShell in the repository directory and run:

```powershell
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml exec backend python manage.py migrate
```

Use Windows Firewall to allow inbound `443` only from the VPN or internal subnet. Do not publish PostgreSQL, Redis, or Meilisearch to the host.
