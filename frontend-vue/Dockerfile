# docs/13 §30：Vue build → static assets → Web server（nginx 静态服务 + /api 反向代理）。
# 本地开发建议直接用 `npm run dev`（vite 代理 /api → 127.0.0.1:8000）。

# --- build stage ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# --- serve stage ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
