# ── Build stage ───────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer cache)
COPY package.json yarn.lock ./
COPY packages/shared/package.json          ./packages/shared/
COPY packages/memory-core/package.json     ./packages/memory-core/
COPY packages/orchestrator/package.json    ./packages/orchestrator/
COPY packages/self-healing/package.json    ./packages/self-healing/
COPY packages/tool-gateway/package.json    ./packages/tool-gateway/

RUN yarn install --frozen-lockfile

# Copy source and build
COPY tsconfig.json ./
COPY packages/shared/          ./packages/shared/
COPY packages/memory-core/     ./packages/memory-core/
COPY packages/orchestrator/    ./packages/orchestrator/
COPY packages/self-healing/    ./packages/self-healing/
COPY packages/tool-gateway/    ./packages/tool-gateway/

RUN yarn build

# ── Production stage ──────────────────────────────────────────────────────
FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

# Install production deps only
COPY package.json yarn.lock ./
COPY packages/shared/package.json          ./packages/shared/
COPY packages/memory-core/package.json     ./packages/memory-core/
COPY packages/orchestrator/package.json    ./packages/orchestrator/
COPY packages/self-healing/package.json    ./packages/self-healing/
COPY packages/tool-gateway/package.json    ./packages/tool-gateway/

RUN yarn install --frozen-lockfile --production

# Copy compiled output from builder
COPY --from=builder /app/packages/shared/dist          ./packages/shared/dist
COPY --from=builder /app/packages/memory-core/dist     ./packages/memory-core/dist
COPY --from=builder /app/packages/orchestrator/dist    ./packages/orchestrator/dist
COPY --from=builder /app/packages/self-healing/dist    ./packages/self-healing/dist
COPY --from=builder /app/packages/tool-gateway/dist    ./packages/tool-gateway/dist

EXPOSE 3000

USER node

CMD ["node", "packages/orchestrator/dist/index.js"]
