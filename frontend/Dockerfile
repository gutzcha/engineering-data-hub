FROM node:22-alpine

WORKDIR /app

COPY . .

RUN if [ -f package-lock.json ]; then npm ci; elif [ -f package.json ]; then npm install; fi

EXPOSE 5173

# Production-oriented default. compose.dev.yaml overrides this with Vite hot reload.
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0"]
