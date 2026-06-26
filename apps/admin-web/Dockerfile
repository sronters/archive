FROM node:24-alpine AS deps
WORKDIR /app
COPY apps/admin-web/package.json apps/admin-web/pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile=false

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/admin-web ./
RUN corepack enable && pnpm build

FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app ./
EXPOSE 3000
CMD ["pnpm", "start"]
