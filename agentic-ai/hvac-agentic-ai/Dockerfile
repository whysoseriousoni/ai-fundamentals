FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Actual command is set per-service in docker-compose.yml
CMD ["python3", "mcp_server/server.py"]
