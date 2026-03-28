// Gateway Service — единая точка входа, маршрутизация и аутентификация.
// Принимает запросы от клиентов, проверяет сессию через Redis,
// и проксирует запросы во внутренние микросервисы.

// @title           Gateway Service API
// @version         1.0
// @description     API Gateway банковского приложения. Единая точка входа для клиентских запросов.

// @host            localhost:8000
// @BasePath        /

// @securityDefinitions.apikey SessionToken
// @in header
// @name X-Session-Token
// @description Сессионный токен, полученный при авторизации

package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"gateway_service/app"
	"gateway_service/config"
	"gateway_service/proxy"
	redisClient "gateway_service/redis"
)

func main() {
	cfg := config.Load()

	// Инициализация Redis-клиентов
	sessions, err := redisClient.NewSessionsClient(cfg.RedisSessionsURL)
	if err != nil {
		log.Fatalf("Ошибка подключения к Redis Sessions: %v", err)
	}
	defer sessions.Close()

	onboarding, err := redisClient.NewOnboardingClient(cfg.RedisOnboardingURL)
	if err != nil {
		log.Fatalf("Ошибка подключения к Redis Onboarding: %v", err)
	}
	defer onboarding.Close()

	// Проверка подключения к Redis
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := sessions.Ping(ctx); err != nil {
		log.Printf("WARN: Redis Sessions недоступен при старте: %v", err)
	}

	// HTTP-клиенты для внутренних сервисов
	services := proxy.NewServiceClients(map[string]string{
		"customer":    cfg.CustomerServiceURL,
		"auth":        cfg.AuthServiceURL,
		"account":     cfg.AccountServiceURL,
		"transaction": cfg.TransactionServiceURL,
		"currency":    cfg.CurrencyServiceURL,
		"metal":       cfg.MetalServiceURL,
	})
	defer services.Close()

	e := app.SetupApp(cfg, sessions, onboarding, services)

	// Graceful shutdown
	go func() {
		addr := fmt.Sprintf(":%s", cfg.Port)
		log.Printf("Gateway Service запущен на %s", addr)
		if err := e.Start(addr); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Ошибка запуска сервера: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Завершение работы Gateway Service...")
	ctx, cancel = context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := e.Shutdown(ctx); err != nil {
		log.Fatalf("Ошибка graceful shutdown: %v", err)
	}
	log.Println("Gateway Service остановлен.")
}
