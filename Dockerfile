FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user with numeric UID
RUN useradd -u 10001 -m appuser

# Create logs directory & fix permissions
RUN mkdir -p /app/logs && chown -R 10001:10001 /app

USER 10001

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
