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

// PrepareRequest создает и настраивает HTTP-запрос ко внутреннему сервису.
func (sc *ServiceClients) PrepareRequest(
	c echo.Context,
	method, path string,
	bodyReader io.Reader,
	service, internalAPIKey string,
) (*http.Request, *ServiceClient, error) {
	svc, ok := sc.clients[service]
	if !ok {
		return nil, nil, echo.NewHTTPError(http.StatusInternalServerError, map[string]string{
			"detail": fmt.Sprintf("Неизвестный сервис: %s", service),
		})
	}

	url := svc.BaseURL + path
	req, err := http.NewRequestWithContext(c.Request().Context(), method, url, bodyReader)
	if err != nil {
		return nil, nil, echo.NewHTTPError(http.StatusInternalServerError, map[string]string{
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

	return req, svc, nil
}

// doAndStream выполняется запрос и передает ответ клиенту через Echo.Context.
func (sc *ServiceClients) doAndStream(c echo.Context, svc *ServiceClient, req *http.Request) error {
	resp, err := svc.HTTP.Do(req)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadGateway, map[string]string{
			"detail": "Внутренний сервис недоступен.",
		})
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, map[string]string{
			"detail": "Ошибка чтения ответа от сервиса.",
		})
	}

	contentType := resp.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/json"
	}
	return c.Blob(resp.StatusCode, contentType, respBody)
}

// ForwardRequest пересылает запрос с Go-структурой во внутренний сервис.
func (sc *ServiceClients) ForwardRequest(
	c echo.Context,
	method, path string,
	body interface{},
	service string,
	internalAPIKey string,
) error {
	var bodyReader io.Reader
	if body != nil {
		jsonBytes, err := json.Marshal(body)
		if err != nil {
			return echo.NewHTTPError(http.StatusInternalServerError, map[string]string{
				"detail": "Ошибка сериализации запроса.",
			})
		}
		bodyReader = bytes.NewReader(jsonBytes)
	}

	req, svc, err := sc.PrepareRequest(c, method, path, bodyReader, service, internalAPIKey)
	if err != nil {
		return err
	}

	return sc.doAndStream(c, svc, req)
}

// ForwardRaw пересылает сырое тело запроса во внутренний сервис.
func (sc *ServiceClients) ForwardRaw(
	c echo.Context,
	method, path string,
	rawBody []byte,
	service string,
	internalAPIKey string,
) error {
	var bodyReader io.Reader
	if rawBody != nil {
		bodyReader = bytes.NewReader(rawBody)
	}

	req, svc, err := sc.PrepareRequest(c, method, path, bodyReader, service, internalAPIKey)
	if err != nil {
		return err
	}

	return sc.doAndStream(c, svc, req)
}

// ForwardAndParse пересылает запрос и парсит JSON-ответ.
func (sc *ServiceClients) ForwardAndParse(
	c echo.Context,
	method, path string,
	rawBody []byte,
	service, internalAPIKey string,
) (map[string]interface{}, int, error) {
	var bodyReader io.Reader
	if rawBody != nil {
		bodyReader = bytes.NewReader(rawBody)
	}

	req, svc, err := sc.PrepareRequest(c, method, path, bodyReader, service, internalAPIKey)
	if err != nil {
		return nil, http.StatusInternalServerError, err
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
