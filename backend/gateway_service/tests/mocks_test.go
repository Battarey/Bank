package tests

import (
	"context"
	"time"
)

// MockSessionStore — ручной мок для SessionStore.
type MockSessionStore struct {
	sessions map[string]map[string]string
}

func NewMockSessionStore() *MockSessionStore {
	return &MockSessionStore{
		sessions: make(map[string]map[string]string),
	}
}

func (m *MockSessionStore) SaveToken(ctx context.Context, token, userID string, payload map[string]string, ttl time.Duration) error {
	data := map[string]string{"user_id": userID}
	for k, v := range payload {
		data[k] = v
	}
	m.sessions[token] = data
	return nil
}

func (m *MockSessionStore) LoadToken(ctx context.Context, token string) (map[string]string, error) {
	return m.sessions[token], nil
}

func (m *MockSessionStore) TouchToken(ctx context.Context, token, userID string, ttl time.Duration) error {
	return nil
}

func (m *MockSessionStore) UpdateTokenData(ctx context.Context, token string, data map[string]string) error {
	if s, ok := m.sessions[token]; ok {
		for k, v := range data {
			s[k] = v
		}
	}
	return nil
}

func (m *MockSessionStore) DeleteToken(ctx context.Context, token string) error {
	delete(m.sessions, token)
	return nil
}

func (m *MockSessionStore) RevokeAll(ctx context.Context, userID string) error {
	for k, v := range m.sessions {
		if v["user_id"] == userID {
			delete(m.sessions, k)
		}
	}
	return nil
}

func (m *MockSessionStore) Close() error {
	return nil
}

// MockOnboardingStore — ручной мок для OnboardingStore.
type MockOnboardingStore struct {
	tokens map[string]string
}

func NewMockOnboardingStore() *MockOnboardingStore {
	return &MockOnboardingStore{
		tokens: make(map[string]string),
	}
}

func (m *MockOnboardingStore) SaveOnboardingToken(ctx context.Context, token, userID string, ttl time.Duration) error {
	m.tokens[token] = userID
	return nil
}

func (m *MockOnboardingStore) LoadOnboardingToken(ctx context.Context, token string) (string, error) {
	return m.tokens[token], nil
}

func (m *MockOnboardingStore) TouchOnboardingToken(ctx context.Context, token string, ttl time.Duration) error {
	return nil
}

func (m *MockOnboardingStore) DeleteOnboardingToken(ctx context.Context, token string) error {
	delete(m.tokens, token)
	return nil
}

func (m *MockOnboardingStore) Close() error {
	return nil
}
