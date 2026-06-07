# Linux Server Install

1. Install Docker Engine with the Compose plugin from your OS vendor or Docker's official packages.
2. Create a deployment directory, for example `/opt/plastic-engineering-data-hub`, and copy the repository there.
3. Copy `.env.example` to `.env` and replace all placeholder secrets, hostnames, database credentials, and Caddy certificate paths.
4. Ask IT to create internal DNS for `APP_HOST` and place the certificate/key files under `ops/caddy/certs/` with paths matching `CADDY_TLS_DIRECTIVE`.
5. Start the stack:

```sh
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml exec backend python manage.py migrate
```

Keep ports other than `443` off the host firewall. Expose `443` only on the VPN or internal network interface.
