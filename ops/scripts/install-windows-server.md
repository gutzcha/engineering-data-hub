<!--
===
File Summary
Path: ops\scripts\install-windows-server.md
Type: markdown
Purpose: Operational automation scripts and deployment helpers.
Primary responsibilities:
- Domain behavior is summarized for fast onboarding and avoids full-file reread.
- Core symbols: Windows Server Install
Inputs:
- Downstream and upstream interactions in the same domain.
Outputs:
- API payloads, records, side effects, or UI views depending on file role.
Dependencies:
- Shared runtime services and adjacent domain modules.
Known risks:
- Validate behavior after migrations, dependency upgrades, or contract changes.
===

-->

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

