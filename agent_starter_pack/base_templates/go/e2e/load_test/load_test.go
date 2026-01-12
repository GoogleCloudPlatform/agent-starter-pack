//go:build load
// +build load

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

// Package loadtest contains load tests for the agent server using A2A protocol.
package loadtest

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/google/uuid"
)

var (
	stagingURL = flag.String("staging-url", "", "Staging server URL")
	duration   = flag.Duration("duration", 30*time.Second, "Load test duration")
	users      = flag.Int("users", 10, "Number of concurrent users")
	ramp       = flag.Float64("ramp", 0.5, "Ramp-up rate (users per second)")
)

const a2aEndpoint = "/a2a/invoke"

// LoadTestResults holds the results of the load test.
type LoadTestResults struct {
	TotalRequests int64
	SuccessCount  int64
	FailureCount  int64
	RateLimited   int64
	Latencies     []int64
	Errors        []string
	mu            sync.Mutex
	startTime     time.Time
}

func (r *LoadTestResults) addSuccess(latencyMs int64) {
	atomic.AddInt64(&r.TotalRequests, 1)
	atomic.AddInt64(&r.SuccessCount, 1)
	r.mu.Lock()
	r.Latencies = append(r.Latencies, latencyMs)
	r.mu.Unlock()
}

func (r *LoadTestResults) addFailure(err string) {
	atomic.AddInt64(&r.TotalRequests, 1)
	atomic.AddInt64(&r.FailureCount, 1)
	r.mu.Lock()
	r.Errors = append(r.Errors, err)
	r.mu.Unlock()
}

func (r *LoadTestResults) addRateLimited() {
	atomic.AddInt64(&r.RateLimited, 1)
}

func (r *LoadTestResults) percentile(p float64) int64 {
	if len(r.Latencies) == 0 {
		return 0
	}
	sorted := make([]int64, len(r.Latencies))
	copy(sorted, r.Latencies)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i] < sorted[j] })
	idx := int(float64(len(sorted)-1) * p)
	return sorted[idx]
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

type messageSendParams struct {
	Message a2aMessageWithContext `json:"message"`
}

type a2aMessageWithContext struct {
	Role      string    `json:"role"`
	Parts     []a2aPart `json:"parts"`
	ContextID string    `json:"contextId,omitempty"`
}

// TestLoad runs the load test against the staging server using A2A protocol.
func TestLoad(t *testing.T) {
	flag.Parse()

	baseURL := *stagingURL
	if baseURL == "" {
		baseURL = os.Getenv("_STAGING_URL")
	}
	if baseURL == "" {
		t.Skip("No staging URL provided, skipping load test")
	}

	idToken := os.Getenv("_ID_TOKEN")

	log.Printf("═══════════════════════════════════════════════════════════════")
	log.Printf("  A2A LOAD TEST CONFIGURATION")
	log.Printf("═══════════════════════════════════════════════════════════════")
	log.Printf("  Target URL:     %s", baseURL)
	log.Printf("  A2A Endpoint:   %s", a2aEndpoint)
	log.Printf("  Duration:       %s", *duration)
	log.Printf("  Concurrent Users: %d", *users)
	log.Printf("  Ramp-up Rate:   %.1f users/sec", *ramp)
	log.Printf("═══════════════════════════════════════════════════════════════")

	results := &LoadTestResults{startTime: time.Now()}
	var wg sync.WaitGroup
	done := make(chan struct{})

	// Start timer
	go func() {
		time.Sleep(*duration)
		close(done)
	}()

	// Ramp up users
	rampInterval := time.Duration(float64(time.Second) / *ramp)
	for i := 0; i < *users; i++ {
		wg.Add(1)
		go func(userNum int) {
			defer wg.Done()
			runUser(baseURL, idToken, results, done)
		}(i)
		time.Sleep(rampInterval)
	}

	wg.Wait()
	totalDuration := time.Since(results.startTime)

	// Calculate stats
	var avgLatency, minLatency, maxLatency float64
	var p50, p95, p99 int64
	if results.SuccessCount > 0 {
		var totalLatency int64
		minLatency = float64(results.Latencies[0])
		maxLatency = float64(results.Latencies[0])
		for _, l := range results.Latencies {
			totalLatency += l
			if float64(l) < minLatency {
				minLatency = float64(l)
			}
			if float64(l) > maxLatency {
				maxLatency = float64(l)
			}
		}
		avgLatency = float64(totalLatency) / float64(results.SuccessCount)
		p50 = results.percentile(0.50)
		p95 = results.percentile(0.95)
		p99 = results.percentile(0.99)
	}

	rps := float64(results.TotalRequests) / totalDuration.Seconds()
	successRate := float64(results.SuccessCount) / float64(results.TotalRequests) * 100

	log.Printf("")
	log.Printf("═══════════════════════════════════════════════════════════════")
	log.Printf("  A2A LOAD TEST RESULTS")
	log.Printf("═══════════════════════════════════════════════════════════════")
	log.Printf("  Duration:       %.2fs", totalDuration.Seconds())
	log.Printf("")
	log.Printf("  REQUESTS")
	log.Printf("  ─────────────────────────────────────────────────────────────")
	log.Printf("  Total:          %d", results.TotalRequests)
	log.Printf("  Successful:     %d (%.1f%%)", results.SuccessCount, successRate)
	log.Printf("  Failed:         %d", results.FailureCount)
	log.Printf("  Rate Limited:   %d", results.RateLimited)
	log.Printf("  Throughput:     %.2f req/sec", rps)
	log.Printf("")
	log.Printf("  LATENCY (ms)")
	log.Printf("  ─────────────────────────────────────────────────────────────")
	log.Printf("  Min:            %.0f", minLatency)
	log.Printf("  Avg:            %.0f", avgLatency)
	log.Printf("  Max:            %.0f", maxLatency)
	log.Printf("  P50:            %d", p50)
	log.Printf("  P95:            %d", p95)
	log.Printf("  P99:            %d", p99)
	log.Printf("═══════════════════════════════════════════════════════════════")

	// Print errors if any
	if len(results.Errors) > 0 {
		log.Printf("")
		log.Printf("  ERRORS (first 5)")
		log.Printf("  ─────────────────────────────────────────────────────────────")
		for i, err := range results.Errors {
			if i >= 5 {
				log.Printf("  ... and %d more errors", len(results.Errors)-5)
				break
			}
			log.Printf("  %d. %s", i+1, err)
		}
	}

	// Fail if too many failures
	failureRate := float64(results.FailureCount) / float64(results.TotalRequests)
	if failureRate > 0.1 {
		t.Errorf("Failure rate too high: %.2f%%", failureRate*100)
	}
}

func runUser(baseURL, idToken string, results *LoadTestResults, done <-chan struct{}) {
	client := &http.Client{Timeout: 60 * time.Second}

	for {
		select {
		case <-done:
			return
		default:
			if err := runA2AMessage(client, baseURL, idToken, results); err != nil {
				results.addFailure(err.Error())
			}
			// Wait between requests (1-3 seconds)
			time.Sleep(time.Duration(1+time.Now().UnixNano()%2) * time.Second)
		}
	}
}

func runA2AMessage(client *http.Client, baseURL, idToken string, results *LoadTestResults) error {
	headers := map[string]string{
		"Content-Type": "application/json",
	}
	if idToken != "" {
		headers["Authorization"] = "Bearer " + idToken
	}

	// Create A2A JSON-RPC request
	contextID := uuid.New().String()
	request := jsonRPCRequest{
		JSONRPC: "2.0",
		Method:  "message/send",
		ID:      uuid.New().String(),
		Params: messageSendParams{
			Message: a2aMessageWithContext{
				Role:      "user",
				Parts:     []a2aPart{{Kind: "text", Text: "Hello! Weather in New York?"}},
				ContextID: contextID,
			},
		},
	}

	startTime := time.Now()

	body, err := json.Marshal(request)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequest("POST", baseURL+a2aEndpoint, bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send A2A message: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("A2A failed: %d - %s", resp.StatusCode, string(respBody))
	}

	// Read full response body
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response: %w", err)
	}

	// Try parsing as direct JSON-RPC response first
	var jsonRPCResp map[string]interface{}
	if err := json.Unmarshal(respBody, &jsonRPCResp); err == nil {
		// Check for JSON-RPC error
		if errObj, ok := jsonRPCResp["error"].(map[string]interface{}); ok {
			msg := errObj["message"]
			return fmt.Errorf("A2A error: %v", msg)
		}

		// Check for successful result with task status
		if result, ok := jsonRPCResp["result"].(map[string]interface{}); ok {
			if status, ok := result["status"].(map[string]interface{}); ok {
				if state, ok := status["state"].(string); ok {
					if state == "completed" {
						latency := time.Since(startTime).Milliseconds()
						results.addSuccess(latency)
						return nil
					}
					if state == "failed" {
						msg := status["message"]
						return fmt.Errorf("task failed: %v", msg)
					}
				}
			}
			// Result exists but no terminal state - still consider success
			latency := time.Since(startTime).Milliseconds()
			results.addSuccess(latency)
			return nil
		}
	}

	// Fall back to SSE parsing if not valid JSON-RPC
	scanner := bufio.NewScanner(bytes.NewReader(respBody))
	scanner.Buffer(make([]byte, 64*1024), 1024*1024)

	var taskCompleted bool
	var eventCount int

	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, "429 Too Many Requests") {
			results.addRateLimited()
		}
		if strings.HasPrefix(line, "data: ") {
			eventJSON := strings.TrimPrefix(line, "data: ")
			var event map[string]interface{}
			if err := json.Unmarshal([]byte(eventJSON), &event); err == nil {
				eventCount++
				if result, ok := event["result"].(map[string]interface{}); ok {
					if status, ok := result["status"].(map[string]interface{}); ok {
						if state, ok := status["state"].(string); ok {
							if state == "completed" || state == "failed" || state == "canceled" {
								taskCompleted = true
							}
						}
					}
				}
			}
		}
	}

	if taskCompleted || eventCount > 0 {
		latency := time.Since(startTime).Milliseconds()
		results.addSuccess(latency)
		return nil
	}

	return fmt.Errorf("no valid A2A response received")
}
