
# 亚马逊利润计算器（Zeabur 部署版）

## 本地运行
```bash
pip install -r requirements.txt
streamlit run app.py
# 浏览器打开 http://localhost:8501
```

## Zeabur 部署（两种方式）

### A) 无 Dockerfile（Buildpack 自动识别 Python）
1. 将本仓库推到 GitHub。
2. Zeabur -> Create Service -> 选择 GitHub 仓库。
3. 语言/框架选择 **Python**（或自动识别）。
4. **Start Command** 填入：
   ```
   streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT
   ```
5. 部署即可访问。以后改代码，点 **Clear Cache & Redeploy** 生效。

### B) 使用 Dockerfile
1. 保持仓库含 `Dockerfile`。
2. Zeabur 选择 **Docker** 方式部署。
3. 其他保持默认即可。

## 环境变量
- 无需自定义。平台会提供 `PORT`。

## 常见问题
- 页面空白/静态站点：确保 Start Command 正确，且选择 Python 或 Docker，而不是 Static。
- 端口占用：必须监听 `0.0.0.0` 且端口为 `$PORT`。
- 修改后不生效：使用 **Clear Cache & Redeploy**。
