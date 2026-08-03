# ============================================================
# 采购库存 BI Dashboard — Docker 镜像
# 前后端一体化打包：Node 构建前端 + Python 运行 Flask 服务
# ============================================================

# ── Stage 1: 构建前端 ─────────────────────────────────────
FROM node:22-alpine AS frontend-build

# 👇 1. 设置工作目录到 frontend
WORKDIR /app/frontend

# 👇 2. 切换 npm 源
RUN npm config set registry https://registry.npmmirror.com

# 👇 3. 只复制依赖文件，利用缓存
COPY frontend/package.json frontend/package-lock.json ./

# 👇 4. 安装依赖
RUN npm ci --no-audit --no-fund

# 👇 5. 复制前端源码
COPY frontend/ ./

# 👇 6. 执行构建
RUN npx vite build

# ── Stage 2: 生产运行镜像 ─────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# 👇 7. 为 pip 配置国内源 (你的写法完全正确)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --no-compile -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt \
    && rm -rf /root/.cache/pip /tmp/*

# 👇 8. 复制后端代码
COPY backend/ ./

# 👇 9. 复制前端构建产物
# 注意路径要和 Stage 1 中的 WORKDIR 对应
COPY --from=frontend-build /app/frontend/dist ./static

# 👇 10. 清理无用文件
RUN rm -rf __pycache__ data

# 👇 11. 环境变量和启动命令
ENV PYTHONUNBUFFERED=1
ENV STATIC_FOLDER=/app/static

EXPOSE 5001

CMD ["python", "app.py"]