# PAMASMMA v4 — Frontend Dockerfile
# Next.js standalone build. Non-root. Railway-ready.

FROM node:20-alpine AS base
WORKDIR /app
ENV NODE_ENV=production

# ── Deps ─────────────────────────────────────────────────────────────────────
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# ── Builder ───────────────────────────────────────────────────────────────────
FROM base AS builder
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# ── Runner ────────────────────────────────────────────────────────────────────
FROM base AS runner
RUN addgroup --system pamasmma && adduser --system --ingroup pamasmma pamasmma

COPY --from=builder --chown=pamasmma:pamasmma /app/.next/standalone ./
COPY --from=builder --chown=pamasmma:pamasmma /app/.next/static ./.next/static
COPY --from=builder --chown=pamasmma:pamasmma /app/public ./public

USER pamasmma
EXPOSE 3000

CMD ["sh", "-c", "node server.js"]
