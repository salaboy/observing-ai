# Stage 1: Build the React frontend
FROM node:22-slim AS frontend
WORKDIR /build
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci
COPY webapp/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.13-slim
WORKDIR /app

# Install Python dependencies first (cached layer)
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY app/ app/

# Copy built frontend from stage 1
COPY --from=frontend /static static/

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
