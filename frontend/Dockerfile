# 前端：多阶段构建（node 编译 → nginx 托管静态文件）
# build context = frontend/ 目录（compose 里 build.context: ./frontend）

# ── 阶段1: 构建 ──
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build          # 产出 dist/

# ── 阶段2: 托管 ──
FROM nginx:alpine
# nginx 配置：托管 dist + /api 反代到 backend 容器
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
