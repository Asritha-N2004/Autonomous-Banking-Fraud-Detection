FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend /app/backend
COPY scripts /app/scripts
RUN useradd -m banking && mkdir -p /app/models /app/data/synthetic /app/data/processed && chown -R banking:banking /app
USER banking
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
