package routes



import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// MetalHandler обрабатывает маршруты metal_service.
type MetalHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterMetalRoutes регистрирует маршруты драгоценных металлов.
func (h *MetalHandler) RegisterMetalRoutes(e *echo.Echo) {
	e.GET("/metals/rates", h.GetMetalRates)
}

// GetMetalRates godoc
func (h *MetalHandler) GetMetalRates(c echo.Context) error {
	base := c.QueryParam("base")
	if base == "" {
		base = "RUB"
	}
	path := fmt.Sprintf("/metals/rates?base=%s", base)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "metal", h.APIKey)
}
