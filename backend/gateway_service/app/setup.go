package app

import (
	"net/http"

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

// SetupApp настраивает экземпляр Echo и возвращает его.
func SetupApp(
	cfg *config.Config,
	sessions redisClient.SessionStore,
	onboarding redisClient.OnboardingStore,
	services *proxy.ServiceClients,
) *echo.Echo {
	e := echo.New()
	e.HideBanner = true

	// CORS
	e.Use(echoMiddleware.CORSWithConfig(echoMiddleware.CORSConfig{
		AllowOrigins:     cfg.CORSAllowedOrigins,
		AllowCredentials: true,
		AllowMethods:     []string{http.MethodGet, http.MethodPost, http.MethodPut, http.MethodPatch, http.MethodDelete, http.MethodOptions},
		AllowHeaders:     []string{"*"},
	}))

	// Middleware: логирование + recover + rate limiting + аутентификация
	e.Use(echoMiddleware.Logger())
	e.Use(echoMiddleware.Recover())
	e.Use(echoMiddleware.RateLimiter(echoMiddleware.NewRateLimiterMemoryStore(20)))
	e.Use(middleware.AuthMiddleware(sessions))

	// Swagger UI
	e.GET("/docs", func(c echo.Context) error {
		return c.Redirect(http.StatusMovedPermanently, "/docs/index.html")
	})
	e.GET("/docs/*", echoSwagger.WrapHandler)

	// Healthcheck
	e.GET("/health", routes.Health)

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

	return e
}
