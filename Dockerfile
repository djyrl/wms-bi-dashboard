# ============================================================
# 采购库存 BI Dashboard — Docker 镜像
# 前后端一体化打包：Node 构建前端 + Python 运行 Flask 服务
# ============================================================

# ── Stage 1: 构建前端 ─────────────────────────────────────
FROM node:22-alpine AS frontend-build

WORKDIR /build

# 安装依赖（利用 Docker 缓存层）
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --prefer-offline --no-audit

# 复制前端源码并构建（跳过 vue-tsc 严格检查，CI 环境已单独验证）
COPY frontend/ ./
RUN npx vite build

# ── Stage 2: 生产运行镜像 ─────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# 安装 Python 依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制后端代码
COPY backend/ ./

# 复制前端构建产物到 static 目录（Flask 统管静态文件）
COPY --from=frontend-build /build/dist ./static

# 清理无用后端文件（保留 import_erp_catalog.py 供定时任务使用）
RUN rm -rf __pycache__ data

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV STATIC_FOLDER=/app/static

EXPOSE 5001

CMD ["python", "app.py"]
