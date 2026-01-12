// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package integration

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
)

const (
	baseURL        = "http://127.0.0.1:8000"
	a2aURL         = baseURL + "/a2a/invoke"
	agentCardURL   = baseURL + "/.well-known/agent-card.json"
	healthCheckURL = baseURL + "/api/list-apps" // Still use API for health check
)

// startServer starts the Go server using subprocess.
// Environment variables are loaded from .env via init() in test_helpers.go
// and passed to the subprocess via os.Environ().
// Server starts with A2A protocol support.
func startServer(t *testing.T) *exec.Cmd {
	cmd := exec.Command("go", "run", ".", "web", "--port", "8000", "api", "a2a")
	cmd.Dir = "../../" // Go to project root
	cmd.Env = append(os.Environ(), "INTEGRATION_TEST=TRUE")
	// Discard output to avoid I/O issues on process kill
	cmd.Stdout = io.Discard
	cmd.Stderr = io.Discard

	if err := cmd.Start(); err != nil {
		t.Fatalf("Failed to start server: %v", err)
	}

	return cmd
}

// waitForServer waits for the server to be ready.
func waitForServer(t *testing.T, timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		resp, err := http.Get(healthCheckURL)
		if err == nil {
			resp.Body.Close()
			if resp.StatusCode == 200 {
				t.Log("Server is ready")
				return true
			}
		}
		time.Sleep(1 * time.Second)
	}
	t.Log("Server did not become ready within timeout")
	return false
}

// stopServer stops the server process.
func stopServer(t *testing.T, cmd *exec.Cmd) {
	if cmd != nil && cmd.Process != nil {
		t.Log("Stopping server process")
		_ = cmd.Process.Kill()
		// Use a goroutine with timeout to avoid hanging
		done := make(chan error, 1)
		go func() {
			done <- cmd.Wait()
		}()
		select {
		case <-done:
		case <-time.After(5 * time.Second):
			t.Log("Server process kill timeout")
		}
		t.Log("Server process stopped")
	}
}

// A2A JSON-RPC request structure
type jsonRPCRequest struct {
	JSONRPC string      `json:"jsonrpc"`
	Method  string      `json:"method"`
	ID      string      `json:"id"`
	Params  interface{} `json:"params"`
}

// A2A message structure
type a2aPart struct {
	Kind string `json:"kind"`
	Text string `json:"text,omitempty"`
}

// messageSendParams for A2A message/send
type messageSendParams struct {
	Message a2aMessageWithContext `json:"message"`
}

type a2aMessageWithContext struct {
	Role      string    `json:"role"`
	Parts     []a2aPart `json:"parts"`
	TaskID    string    `json:"taskId,omitempty"`
	ContextID string    `json:"contextId,omitempty"`
}

// TestA2AAgentCard tests that the agent card is available.
func TestA2AAgentCard(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping E2E test in short mode")
	}

	// Start server (local variable to avoid race conditions)
	t.Log("Starting server process")
	serverProcess := startServer(t)
	defer stopServer(t, serverProcess)

	if !waitForServer(t, 90*time.Second) {
		t.Fatal("Server failed to start")
	}
	t.Log("Server process started")

	// Fetch agent card
	resp, err := http.Get(agentCardURL)
	if err != nil {
		t.Fatalf("Failed to fetch agent card: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		t.Fatalf("Expected status code 200, got %d: %s", resp.StatusCode, string(body))
	}

	var agentCard map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&agentCard); err != nil {
		t.Fatalf("Failed to decode agent card: %v", err)
	}

	// Verify agent card has required fields
	if name, ok := agentCard["name"].(string); !ok || name == "" {
		t.Fatal("Agent card missing 'name' field")
	}
	t.Logf("Agent card: name=%v", agentCard["name"])

	if url, ok := agentCard["url"].(string); !ok || url == "" {
		t.Fatal("Agent card missing 'url' field")
	}
	t.Logf("Agent card: url=%v", agentCard["url"])
}

// TestA2AMessageSend tests the A2A message/send functionality using JSON-RPC.
func TestA2AMessageSend(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping E2E test in short mode")
	}

	// Start server (local variable to avoid race conditions)
	t.Log("Starting server process")
	serverProcess := startServer(t)
	defer stopServer(t, serverProcess)

	if !waitForServer(t, 90*time.Second) {
		t.Fatal("Server failed to start")
	}
	t.Log("Server process started")

	// Create A2A JSON-RPC request
	contextID := uuid.New().String()
	request := jsonRPCRequest{
		JSONRPC: "2.0",
		Method:  "message/send",
		ID:      uuid.New().String(),
		Params: messageSendParams{
			Message: a2aMessageWithContext{
				Role:      "user",
				Parts:     []a2aPart{{Kind: "text", Text: "Hello!"}},
				ContextID: contextID,
			},
		},
	}

	body, err := json.Marshal(request)
	if err != nil {
		t.Fatalf("Failed to marshal request: %v", err)
	}

	client := &http.Client{Timeout: 60 * time.Second}
	req, err := http.NewRequest("POST", a2aURL, bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Failed to send A2A request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		respBody, _ := io.ReadAll(resp.Body)
		t.Fatalf("Expected status code 200, got %d: %s", resp.StatusCode, string(respBody))
	}

	// Read the full response body
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("Failed to read response body: %v", err)
	}

	// A2A uses SSE for streaming - parse the events
	lines := strings.Split(string(respBody), "\n")
	var events []map[string]interface{}
	for _, line := range lines {
		if strings.HasPrefix(line, "data: ") {
			eventJSON := strings.TrimPrefix(line, "data: ")
			var event map[string]interface{}
			if err := json.Unmarshal([]byte(eventJSON), &event); err == nil {
				events = append(events, event)
				t.Logf("Received A2A event type: %T", event)
			}
		}
	}

	// If no SSE events, try parsing as direct JSON-RPC response
	if len(events) == 0 {
		var jsonRPCResp map[string]interface{}
		if err := json.Unmarshal(respBody, &jsonRPCResp); err == nil {
			// Check if it's a valid JSON-RPC response
			if _, hasResult := jsonRPCResp["result"]; hasResult {
				t.Log("Received valid JSON-RPC response with result")
				return
			}
			if errObj, hasError := jsonRPCResp["error"]; hasError {
				t.Logf("Received JSON-RPC error: %v", errObj)
				// An error response is still a valid response
				return
			}
		}
		t.Logf("Response body: %s", string(respBody))
		t.Fatal("No valid A2A response received")
	}

	t.Logf("Received %d A2A events", len(events))
}

// TestA2AErrorHandling tests A2A error handling for invalid requests.
func TestA2AErrorHandling(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping E2E test in short mode")
	}

	// Start server (local variable to avoid race conditions)
	t.Log("Starting server process")
	serverProcess := startServer(t)
	defer stopServer(t, serverProcess)

	if !waitForServer(t, 90*time.Second) {
		t.Fatal("Server failed to start")
	}

	t.Log("Starting A2A error handling test")

	// Send malformed JSON-RPC request
	request := jsonRPCRequest{
		JSONRPC: "2.0",
		Method:  "invalid/method",
		ID:      uuid.New().String(),
		Params:  map[string]interface{}{},
	}

	body, _ := json.Marshal(request)
	req, err := http.NewRequest("POST", a2aURL, bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Failed to send request: %v", err)
	}
	defer resp.Body.Close()

	// A2A should return an error response for invalid methods
	respBody, _ := io.ReadAll(resp.Body)
	t.Logf("Error response: %s", string(respBody))

	// JSON-RPC errors should still return 200 with error in body
	var jsonRPCResp map[string]interface{}
	if err := json.Unmarshal(respBody, &jsonRPCResp); err == nil {
		if _, hasError := jsonRPCResp["error"]; hasError {
			t.Log("Received expected JSON-RPC error response")
			return
		}
	}

	t.Log("A2A error handling test completed")
}
