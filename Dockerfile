# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace manifests first for layer caching
COPY package.json yarn.lock ./
COPY packages/shared/package.json             ./packages/shared/
COPY packages/memory-core/package.json        ./packages/memory-core/
COPY packages/self-healing/package.json       ./packages/self-healing/
COPY packages/mali-engine/package.json        ./packages/mali-engine/
COPY packages/tool-gateway/package.json       ./packages/tool-gateway/
COPY packages/content-agent/package.json      ./packages/content-agent/
COPY packages/marketing-intel/package.json    ./packages/marketing-intel/
COPY packages/personality-engine/package.json ./packages/personality-engine/
COPY packages/relationship-graph/package.json ./packages/relationship-graph/
COPY packages/orchestrator/package.json       ./packages/orchestrator/

RUN yarn install --frozen-lockfile

# Copy source + tsconfigs
COPY tsconfig.json tsconfig.build.json ./
COPY packages/ ./packages/

RUN yarn build

# ── Production stage ──────────────────────────────────────────────────────────
FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

COPY package.json yarn.lock ./
COPY packages/shared/package.json             ./packages/shared/
COPY packages/memory-core/package.json        ./packages/memory-core/
COPY packages/self-healing/package.json       ./packages/self-healing/
COPY packages/mali-engine/package.json        ./packages/mali-engine/
COPY packages/tool-gateway/package.json       ./packages/tool-gateway/
COPY packages/content-agent/package.json      ./packages/content-agent/
COPY packages/marketing-intel/package.json    ./packages/marketing-intel/
COPY packages/personality-engine/package.json ./packages/personality-engine/
COPY packages/relationship-graph/package.json ./packages/relationship-graph/
COPY packages/orchestrator/package.json       ./packages/orchestrator/

RUN yarn install --frozen-lockfile --production

# Copy compiled dist from builder
COPY --from=builder /app/packages/shared/dist             ./packages/shared/dist
COPY --from=builder /app/packages/memory-core/dist        ./packages/memory-core/dist
COPY --from=builder /app/packages/self-healing/dist       ./packages/self-healing/dist
COPY --from=builder /app/packages/mali-engine/dist        ./packages/mali-engine/dist
COPY --from=builder /app/packages/tool-gateway/dist       ./packages/tool-gateway/dist
COPY --from=builder /app/packages/content-agent/dist      ./packages/content-agent/dist
COPY --from=builder /app/packages/marketing-intel/dist    ./packages/marketing-intel/dist
COPY --from=builder /app/packages/personality-engine/dist ./packages/personality-engine/dist
COPY --from=builder /app/packages/relationship-graph/dist ./packages/relationship-graph/dist
COPY --from=builder /app/packages/orchestrator/dist       ./packages/orchestrator/dist

EXPOSE 3000

USER node

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/api/health || exit 1

CMD ["node", "packages/orchestrator/dist/index.js"]
