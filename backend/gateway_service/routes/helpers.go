package routes

import (
	"bytes"
	"encoding/json"
	"io"

	"github.com/labstack/echo/v4"

	"regexp"
	"gateway_service/proxy"
)

// ReadBody читает тело запроса и возвращает его как []byte (для повторного использования).
func ReadBody(c echo.Context) ([]byte, error) {
	if c.Request().Body == nil {
		return nil, nil
	}
	body, err := io.ReadAll(c.Request().Body)
	if err != nil {
		return nil, err
	}
	c.Request().Body = io.NopCloser(bytes.NewReader(body))
	return body, nil
}

// ForwardAndParse пересылает запрос и парсит JSON-ответ (устарело, используйте sc.ForwardAndParse).
func ForwardAndParse(
	c echo.Context,
	sc *proxy.ServiceClients,
	method, path string,
	rawBody []byte,
	service, apiKey string,
) (map[string]interface{}, int, error) {
	return sc.ForwardAndParse(c, method, path, rawBody, service, apiKey)
}

// JSONToMap конвертирует []byte в map для модификации.
func JSONToMap(data []byte) (map[string]interface{}, error) {
	var m map[string]interface{}
	err := json.Unmarshal(data, &m)
	return m, err
}

// MapToJSON конвертирует map обратно в []byte.
func MapToJSON(m map[string]interface{}) ([]byte, error) {
	return json.Marshal(m)
}

// uuidRegex — регулярное выражение для проверки формата UUID v4 (и других).
var uuidRegex = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)

// ValidateUUID проверяет, является ли строка корректным UUID.
func ValidateUUID(id string) bool {
	return uuidRegex.MatchString(id)
}
