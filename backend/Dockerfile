FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
ENV PORT=8000
ENV PYTHONPATH=/app/backend
# Run as package so package-relative imports (backend.*) resolve reliably
CMD ["python", "-m", "backend.app"]
