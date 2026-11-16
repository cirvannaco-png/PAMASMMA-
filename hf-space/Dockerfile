# PAMASMMA frontend — Hugging Face Docker Space
# Build context is the staged contents of the frontend/ directory.

FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install --include=dev
RUN npm audit --omit=dev --audit-level=high
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=7860
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 7860
CMD ["node", "server.js"]
