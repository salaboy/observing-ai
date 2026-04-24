# --- Build stage ---
FROM golang:1.24-bookworm AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o claude-proxy .

# --- Runtime stage ---
FROM node:22-bookworm-slim

# Install Claude Code globally via npm
RUN npm install -g @anthropic-ai/claude-code

# Copy the Go binary from the build stage
COPY --from=builder /app/claude-proxy /usr/local/bin/claude-proxy

# Pass ANTHROPIC_API_KEY at runtime via: docker run -e ANTHROPIC_API_KEY=sk-ant-...

# OTel defaults: short flush intervals so short-lived `claude --print` processes
# export data before exiting, and http/protobuf for broad compatibility.
ENV OTEL_METRIC_EXPORT_INTERVAL=1000
ENV OTEL_LOGS_EXPORT_INTERVAL=1000
ENV OTEL_TRACES_EXPORT_INTERVAL=1000
ENV OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

EXPOSE 8080

ENTRYPOINT ["claude-proxy"]
