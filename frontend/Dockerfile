# ===
# File Summary
# Path: frontend\Dockerfile
# Type: shell
# Purpose: Container build specification for backend or frontend image publication.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: file-level implementation
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

FROM node:22-alpine

WORKDIR /app

COPY . .

RUN if [ -f package-lock.json ]; then npm ci; elif [ -f package.json ]; then npm install; fi

RUN npm run build

EXPOSE 5173

# Production-oriented default. compose.dev.yaml overrides this with Vite hot reload.
CMD ["npm", "run", "start"]

