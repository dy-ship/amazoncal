
# 使用轻量级 Python 镜像
FROM python:3.11-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# 依赖
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# 代码
COPY app.py /app/app.py

# Zeabur/容器平台会注入 PORT 环境变量
ENV PORT=8080

# 运行 Streamlit，并监听 0.0.0.0:$PORT
CMD ["bash", "-lc", "streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT"]
