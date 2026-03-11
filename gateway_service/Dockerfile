# ── Stage 1: Сборка ──────────────────────────────────────────────────
FROM golang:1.23-alpine AS builder

WORKDIR /build

# Копируем go.mod, go.sum и вендорированные зависимости
COPY go.mod go.sum ./
COPY vendor/ vendor/

# Копируем исходный код и собираем бинарник
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -mod=vendor -ldflags="-s -w" -o gateway .

# ── Stage 2: Минимальный образ ───────────────────────────────────────
FROM alpine:3.19

# Сертификаты для HTTPS-запросов к внутренним сервисам (если понадобятся)
RUN apk add --no-cache ca-certificates

COPY --from=builder /build/gateway /gateway

EXPOSE 8000

CMD ["/gateway"]
