package routes

import (
	"net/http"
	"sync"

	"github.com/labstack/echo/v4"
	"gateway_service/proxy"
	"gateway_service/redis"
	"gateway_service/schemas"
)

// HealthHandler хранит зависимости для проверки здоровья системы.
type HealthHandler struct {
	Sessions       redis.SessionStore
	Onboarding     redis.OnboardingStore
	Proxy          *proxy.ServiceClients
	InternalAPIKey string
}

// Health godoc
// @Summary     Проверка состояния системы
// @Description Возвращает детальный статус всех компонентов бэкенда.
// @Tags        system
// @Produce     json
// @Success     200 {object} schemas.HealthResponse "Система работает нормально"
// @Failure     503 {object} schemas.HealthErrorResponse "Одна из зависимостей недоступна"
// @Router      /health [get]
func (h *HealthHandler) Health(c echo.Context) error {
	ctx := c.Request().Context()
	components := make(map[string]interface{})
	isError := false
	var mu sync.Mutex

	// 1. Проверка Redis сессий
	if err := h.Sessions.Ping(ctx); err != nil {
		components["redis_sessions"] = map[string]string{"status": "error", "detail": err.Error()}
		isError = true
	} else {
		components["redis_sessions"] = map[string]string{"status": "ok"}
	}

	// 2. Проверка Redis онбординга
	if err := h.Onboarding.Ping(ctx); err != nil {
		components["redis_onboarding"] = map[string]string{"status": "error", "detail": err.Error()}
		isError = true
	} else {
		components["redis_onboarding"] = map[string]string{"status": "ok"}
	}

	// 3. Параллельный опрос микросервисов
	services := h.Proxy.ListServices()
	var wg sync.WaitGroup
	for _, svcName := range services {
		wg.Add(1)
		go func(name string) {
			defer wg.Done()
			result, err := h.Proxy.Ping(c, name, h.InternalAPIKey)
			
			mu.Lock()
			defer mu.Unlock()
			if err != nil {
				components[name] = map[string]string{"status": "error", "detail": "Service unreachable"}
				isError = true
			} else {
				components[name] = result
				if result["status"] == "error" {
					isError = true
				}
			}
		}(svcName)
	}
	wg.Wait()

	if isError {
		return c.JSON(http.StatusServiceUnavailable, schemas.HealthErrorResponse{
			Status:     "error",
			Detail:     "One or more dependencies are down",
			Components: components,
		})
	}

	return c.JSON(http.StatusOK, schemas.HealthResponse{
		Status:     "ok",
		Components: components,
	})
}
