// Package proxy реализует пересылку запросов во внутренние сервисы.
package proxy

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/labstack/echo/v4"
)

// ServiceClient хранит HTTP-клиент и URL одного внутреннего сервиса.
type ServiceClient struct {
	BaseURL string
	HTTP    *http.Client
}

// ServiceClients хранит HTTP-клиенты для каждого внутреннего сервиса.
type ServiceClients struct {
	clients map[string]*ServiceClient
}

// NewServiceClients создаёт клиенты для всех внутренних сервисов.
func NewServiceClients(services map[string]string) *ServiceClients {
	sc := &ServiceClients{clients: make(map[string]*ServiceClient, len(services))}
	for name, url := range services {
		sc.clients[name] = &ServiceClient{
			BaseURL: url,
			HTTP: &http.Client{
				Timeout: 30 * time.Second,
			},
		}
	}
	return sc
}

// GetClient возвращает клиент сервиса по имени.
func (sc *ServiceClients) GetClient(service string) *ServiceClient {
	return sc.clients[service]
}

// Close закрывает все HTTP-клиенты.
func (sc *ServiceClients) Close() {
	for _, c := range sc.clients {
		c.HTTP.CloseIdleConnections()
	}
}

// ForwardRequest пересылает запрос с Go-структурой во внутренний сервис.
func (sc *ServiceClients) ForwardRequest(
	c echo.Context,
	method, path string,
	body interface{},
	service string,
	internalAPIKey string,
) error {
	svc, ok := sc.clients[service]
	if !ok {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": fmt.Sprintf("Неизвестный сервис: %s", service),
		})
	}

	var bodyReader io.Reader
	if body != nil {
		jsonBytes, err := json.Marshal(body)
		if err != nil {
			return c.JSON(http.StatusInternalServerError, map[string]string{
				"detail": "Ошибка сериализации запроса.",
			})
		}
		bodyReader = bytes.NewReader(jsonBytes)
	}

	url := svc.BaseURL + path
	req, err := http.NewRequestWithContext(c.Request().Context(), method, url, bodyReader)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": "Ошибка создания запроса.",
		})
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Key", internalAPIKey)

	if userID, ok := c.Get("user_id").(string); ok && userID != "" {
		req.Header.Set("X-User-ID", userID)
	}
	if sessionToken := c.Request().Header.Get("X-Session-Token"); sessionToken != "" {
		req.Header.Set("X-Session-Token", sessionToken)
	}

	resp, err := svc.HTTP.Do(req)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{
			"detail": "Внутренний сервис недоступен.",
		})
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": "Ошибка чтения ответа от сервиса.",
		})
	}

	contentType := resp.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/json"
	}
	return c.Blob(resp.StatusCode, contentType, respBody)
}

// ForwardRaw пересылает сырое тело запроса во внутренний сервис.
func (sc *ServiceClients) ForwardRaw(
	c echo.Context,
	method, path string,
	rawBody []byte,
	service string,
	internalAPIKey string,
) error {
	svc, ok := sc.clients[service]
	if !ok {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": fmt.Sprintf("Неизвестный сервис: %s", service),
		})
	}

	var bodyReader io.Reader
	if rawBody != nil {
		bodyReader = bytes.NewReader(rawBody)
	}

	url := svc.BaseURL + path
	req, err := http.NewRequestWithContext(c.Request().Context(), method, url, bodyReader)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": "Ошибка создания запроса.",
		})
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Internal-Key", internalAPIKey)

	if userID, ok := c.Get("user_id").(string); ok && userID != "" {
		req.Header.Set("X-User-ID", userID)
	}
	if sessionToken := c.Request().Header.Get("X-Session-Token"); sessionToken != "" {
		req.Header.Set("X-Session-Token", sessionToken)
	}

	resp, err := svc.HTTP.Do(req)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{
			"detail": "Внутренний сервис недоступен.",
		})
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": "Ошибка чтения ответа от сервиса.",
		})
	}

	contentType := resp.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/json"
	}
	return c.Blob(resp.StatusCode, contentType, respBody)
}
