# PAMASMMA v4 — Frontend Dockerfile
# Next.js standalone build. Non-root.

FROM node:20-alpine AS base
WORKDIR /app
ENV NODE_ENV=production

# ── Deps ─────────────────────────────────────────────────────────────────────
# ── Builder ───────────────────────────────────────────────────────────────────
FROM base AS builder
COPY package.json package-lock.json* ./
RUN npm install --include=dev
RUN npm audit --omit=dev --audit-level=high
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# ── Runner ────────────────────────────────────────────────────────────────────
FROM base AS runner
RUN addgroup --system pamasmma && adduser --system --ingroup pamasmma pamasmma

COPY --from=builder --chown=pamasmma:pamasmma /app/.next/standalone ./
COPY --from=builder --chown=pamasmma:pamasmma /app/.next/static ./.next/static
USER pamasmma
EXPOSE 3000

CMD ["sh", "-c", "node server.js"]
