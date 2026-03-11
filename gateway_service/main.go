// Gateway Service — единая точка входа, маршрутизация и аутентификация.
// Принимает запросы от клиентов, проверяет сессию через Redis,
// и проксирует запросы во внутренние микросервисы.

// @title           Gateway Service API
// @version         1.0
// @description     API Gateway банковского приложения. Единая точка входа для клиентских запросов: онбординг, аутентификация, управление данными пользователя, счета, транзакции, валюты и металлы.

// @host            localhost:8000
// @BasePath        /

// @securityDefinitions.apikey SessionToken
// @in header
// @name X-Session-Token
// @description Сессионный токен, полученный при авторизации

// @securityDefinitions.apikey OnboardingToken
// @in header
// @name X-Onboarding-Token
// @description Токен онбординга, полученный из /users/start (TTL 15 минут, скользящая экспирация)

// @tag.name onboarding
// @tag.description Регистрация нового клиента: создание аккаунта, заполнение данных по шагам и финализация. Шаги требуют заголовок X-Onboarding-Token.
// @tag.name user-update
// @tag.description Обновление данных авторизованного пользователя. Требует заголовок X-Session-Token.
// @tag.name auth
// @tag.description Аутентификация: вход по PIN-коду, управление сессиями. Защищённые эндпоинты требуют заголовок X-Session-Token.
// @tag.name accounts
// @tag.description Банковские счета: открытие, просмотр, закрытие, заморозка.
// @tag.name transactions
// @tag.description Операции по счетам: пополнение, снятие, переводы, история.
// @tag.name currency
// @tag.description Валютные операции: курсы и обмен между счетами.
// @tag.name metals
// @tag.description Драгоценные металлы: курсы.
// @tag.name health
// @tag.description Проверка работоспособности сервиса.

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

	"github.com/labstack/echo/v4"
	echoMiddleware "github.com/labstack/echo/v4/middleware"
	echoSwagger "github.com/swaggo/echo-swagger"

	"gateway_service/config"
	_ "gateway_service/docs"
	"gateway_service/middleware"
	"gateway_service/proxy"
	redisClient "gateway_service/redis"
	"gateway_service/routes"
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

	// Echo-приложение
	e := echo.New()
	e.HideBanner = true

	// CORS
	e.Use(echoMiddleware.CORSWithConfig(echoMiddleware.CORSConfig{
		AllowOrigins:     cfg.CORSAllowedOrigins,
		AllowCredentials: true,
		AllowMethods:     []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodPatch, http.MethodDelete, http.MethodOptions},
		AllowHeaders:     []string{"*"},
	}))

	// Middleware: логирование + recover + аутентификация
	e.Use(echoMiddleware.Logger())
	e.Use(echoMiddleware.Recover())
	e.Use(middleware.AuthMiddleware(sessions))

	// Swagger UI (доступен без авторизации — middleware пропускает /docs/*)
	e.GET("/docs/*", echoSwagger.WrapHandler)

	// Healthcheck
	// @Summary     Проверка работоспособности
	// @Tags        health
	// @Produce     json
	// @Success     200 {object} map[string]string
	// @Router      /health [get]
	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	// Регистрация маршрутов
	customerHandler := &routes.CustomerHandler{
		Proxy:      services,
		Sessions:   sessions,
		Onboarding: onboarding,
		APIKey:     cfg.InternalAPIKey,
	}
	customerHandler.RegisterCustomerRoutes(e)

	authHandler := &routes.AuthHandler{
		Proxy:    services,
		Sessions: sessions,
		APIKey:   cfg.InternalAPIKey,
	}
	authHandler.RegisterAuthRoutes(e)

	accountHandler := &routes.AccountHandler{
		Proxy:  services,
		APIKey: cfg.InternalAPIKey,
	}
	accountHandler.RegisterAccountRoutes(e)

	transactionHandler := &routes.TransactionHandler{
		Proxy:  services,
		APIKey: cfg.InternalAPIKey,
	}
	transactionHandler.RegisterTransactionRoutes(e)

	currencyHandler := &routes.CurrencyHandler{
		Proxy:  services,
		APIKey: cfg.InternalAPIKey,
	}
	currencyHandler.RegisterCurrencyRoutes(e)

	metalHandler := &routes.MetalHandler{
		Proxy:  services,
		APIKey: cfg.InternalAPIKey,
	}
	metalHandler.RegisterMetalRoutes(e)

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
