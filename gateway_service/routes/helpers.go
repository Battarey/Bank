package routes

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// forwardAndParse пересылает запрос и парсит JSON-ответ (для cases, где нужно обработать ответ).
func forwardAndParse(
	c echo.Context,
	sc *proxy.ServiceClients,
	method, path string,
	rawBody []byte,
	service, apiKey string,
) (map[string]interface{}, int, error) {
	svc := sc.GetClient(service)
	if svc == nil {
		return nil, http.StatusInternalServerError, fmt.Errorf("неизвестный сервис: %s", service)
	}

	var bodyReader io.Reader
	if rawBody != nil {
		bodyReader = bytes.NewReader(rawBody)
	}

	url := svc.BaseURL + path
	req, err := http.NewRequestWithContext(c.Request().Context(), method, url, bodyReader)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Key", apiKey)
	if userID, ok := c.Get("user_id").(string); ok && userID != "" {
		req.Header.Set("X-User-ID", userID)
	}
	if sessionToken := c.Request().Header.Get("X-Session-Token"); sessionToken != "" {
		req.Header.Set("X-Session-Token", sessionToken)
	}

	resp, err := svc.HTTP.Do(req)
	if err != nil {
		return nil, http.StatusBadGateway, err
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, http.StatusInternalServerError, err
	}

	var parsed map[string]interface{}
	if err := json.Unmarshal(respBody, &parsed); err != nil {
		// Если ответ не JSON, возвращаем как текст
		parsed = map[string]interface{}{"detail": string(respBody)}
	}

	return parsed, resp.StatusCode, nil
}
