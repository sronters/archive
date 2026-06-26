FROM node:24-alpine AS build
WORKDIR /app

COPY apps/admin-web/package.json ./
RUN corepack enable \
    && corepack prepare pnpm@10.33.2 --activate \
    && pnpm install --frozen-lockfile=false

COPY apps/admin-web ./
RUN corepack enable \
    && corepack prepare pnpm@10.33.2 --activate \
    && pnpm build

FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app ./
EXPOSE 3000
CMD ["sh", "-c", "corepack enable && corepack prepare pnpm@10.33.2 --activate && pnpm start"]
