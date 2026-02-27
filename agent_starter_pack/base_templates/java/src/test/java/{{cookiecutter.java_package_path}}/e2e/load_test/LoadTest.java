// Copyright 2026 Google LLC
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

package {{cookiecutter.java_package}}.e2e.load_test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Load tests for the A2A server using concurrent users.
 *
 * <p>Configuration via system properties or environment variables:
 * <ul>
 *   <li>staging.url or _STAGING_URL: Target server URL (required)</li>
 *   <li>load.duration: Test duration in seconds (default: 30)</li>
 *   <li>load.users: Number of concurrent users (default: 10)</li>
 *   <li>load.ramp: Ramp-up rate in users per second (default: 2.0)</li>
 *   <li>_ID_TOKEN: Bearer token for authentication (optional)</li>
 * </ul>
 *
 * <p>Run with: mvn test -Dtest=LoadTest -Dstaging.url=http://localhost:8080
 */
@Tag("load")
class LoadTest {

  private static final String A2A_ENDPOINT = "/a2a/remote/v1/message:send";

  private final AtomicLong totalRequests = new AtomicLong(0);
  private final AtomicLong successCount = new AtomicLong(0);
  private final AtomicLong failureCount = new AtomicLong(0);
  private final AtomicLong rateLimited = new AtomicLong(0);
  private final CopyOnWriteArrayList<Long> latencies = new CopyOnWriteArrayList<>();
  private final CopyOnWriteArrayList<String> errors = new CopyOnWriteArrayList<>();

  @Test
  void testLoad() throws Exception {
    // Configuration
    String baseUrl = getConfig("staging.url", "_STAGING_URL", null);
    if (baseUrl == null || baseUrl.isEmpty()) {
      System.out.println("No staging URL provided, skipping load test");
      return;
    }

    int durationSeconds = Integer.parseInt(getConfig("load.duration", "LOAD_DURATION", "30"));
    int users = Integer.parseInt(getConfig("load.users", "LOAD_USERS", "10"));
    double ramp = Double.parseDouble(getConfig("load.ramp", "LOAD_RAMP", "2.0"));
    String idToken = System.getenv("_ID_TOKEN");

    System.out.println("═══════════════════════════════════════════════════════════════");
    System.out.println("  A2A LOAD TEST CONFIGURATION");
    System.out.println("═══════════════════════════════════════════════════════════════");
    System.out.printf("  Target URL:       %s%n", baseUrl);
    System.out.printf("  A2A Endpoint:     %s%n", A2A_ENDPOINT);
    System.out.printf("  Duration:         %ds%n", durationSeconds);
    System.out.printf("  Concurrent Users: %d%n", users);
    System.out.printf("  Ramp-up Rate:     %.1f users/sec%n", ramp);
    System.out.println("═══════════════════════════════════════════════════════════════");

    Instant startTime = Instant.now();
    Duration duration = Duration.ofSeconds(durationSeconds);
    CountDownLatch doneLatch = new CountDownLatch(1);
    ExecutorService executor = Executors.newFixedThreadPool(users);

    // Schedule test end
    Executors.newSingleThreadScheduledExecutor().schedule(
        doneLatch::countDown, durationSeconds, TimeUnit.SECONDS
    );

    // Ramp up users
    long rampIntervalMs = (long) (1000.0 / ramp);
    for (int i = 0; i < users; i++) {
      final int userNum = i;
      executor.submit(() -> runUser(baseUrl, idToken, doneLatch, userNum));
      Thread.sleep(rampIntervalMs);
    }

    // Wait for test to complete
    doneLatch.await();
    executor.shutdownNow();
    executor.awaitTermination(5, TimeUnit.SECONDS);

    Duration totalDuration = Duration.between(startTime, Instant.now());
    printResults(totalDuration);

    // Fail if too many failures
    double failureRate = (double) failureCount.get() / totalRequests.get();
    if (failureRate > 0.1) {
      throw new AssertionError(
          String.format("Failure rate too high: %.2f%%", failureRate * 100)
      );
    }
  }

  private void runUser(String baseUrl, String idToken, CountDownLatch done, int userNum) {
    HttpClient client = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(10))
        .build();

    while (done.getCount() > 0) {
      try {
        sendA2AMessage(client, baseUrl, idToken);
        // Wait between requests (1-3 seconds)
        Thread.sleep(1000 + (System.nanoTime() % 2000));
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        break;
      } catch (Exception e) {
        addFailure(e.getMessage());
      }
    }
  }

  private void sendA2AMessage(HttpClient client, String baseUrl, String idToken)
      throws Exception {
    String messageId = UUID.randomUUID().toString();
    String requestBody = String.format("""
        {
            "jsonrpc": "2.0",
            "id": "%s",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "messageId": "%s",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Hello! Weather in New York?"}]
                }
            }
        }
        """, messageId, messageId);

    HttpRequest.Builder requestBuilder = HttpRequest.newBuilder()
        .uri(URI.create(baseUrl + A2A_ENDPOINT))
        .header("Content-Type", "application/json")
        .timeout(Duration.ofSeconds(60))
        .POST(HttpRequest.BodyPublishers.ofString(requestBody));

    if (idToken != null && !idToken.isEmpty()) {
      requestBuilder.header("Authorization", "Bearer " + idToken);
    }

    Instant start = Instant.now();
    HttpResponse<String> response = client.send(
        requestBuilder.build(),
        HttpResponse.BodyHandlers.ofString()
    );
    long latencyMs = Duration.between(start, Instant.now()).toMillis();

    totalRequests.incrementAndGet();

    if (response.statusCode() == 429) {
      rateLimited.incrementAndGet();
      addFailure("Rate limited (429)");
      return;
    }

    if (response.statusCode() != 200) {
      addFailure("HTTP " + response.statusCode() + ": " + response.body());
      return;
    }

    String body = response.body();

    // Check for JSON-RPC error
    if (body.contains("\"error\"")) {
      addFailure("JSON-RPC error: " + body);
      return;
    }

    // Success
    successCount.incrementAndGet();
    latencies.add(latencyMs);
  }

  private void addFailure(String error) {
    failureCount.incrementAndGet();
    if (errors.size() < 100) {
      errors.add(error);
    }
  }

  private void printResults(Duration totalDuration) {
    List<Long> sortedLatencies = new ArrayList<>(latencies);
    Collections.sort(sortedLatencies);

    double avgLatency = 0;
    long minLatency = 0;
    long maxLatency = 0;
    long p50 = 0;
    long p95 = 0;
    long p99 = 0;

    if (!sortedLatencies.isEmpty()) {
      long sum = sortedLatencies.stream().mapToLong(Long::longValue).sum();
      avgLatency = (double) sum / sortedLatencies.size();
      minLatency = sortedLatencies.get(0);
      maxLatency = sortedLatencies.get(sortedLatencies.size() - 1);
      p50 = percentile(sortedLatencies, 0.50);
      p95 = percentile(sortedLatencies, 0.95);
      p99 = percentile(sortedLatencies, 0.99);
    }

    double rps = totalRequests.get() / (totalDuration.toMillis() / 1000.0);
    double successRate = totalRequests.get() > 0
        ? (double) successCount.get() / totalRequests.get() * 100
        : 0;

    System.out.println();
    System.out.println("═══════════════════════════════════════════════════════════════");
    System.out.println("  A2A LOAD TEST RESULTS");
    System.out.println("═══════════════════════════════════════════════════════════════");
    System.out.printf("  Duration:       %.2fs%n", totalDuration.toMillis() / 1000.0);
    System.out.println();
    System.out.println("  REQUESTS");
    System.out.println("  ─────────────────────────────────────────────────────────────");
    System.out.printf("  Total:          %d%n", totalRequests.get());
    System.out.printf("  Successful:     %d (%.1f%%)%n", successCount.get(), successRate);
    System.out.printf("  Failed:         %d%n", failureCount.get());
    System.out.printf("  Rate Limited:   %d%n", rateLimited.get());
    System.out.printf("  Throughput:     %.2f req/sec%n", rps);
    System.out.println();
    System.out.println("  LATENCY (ms)");
    System.out.println("  ─────────────────────────────────────────────────────────────");
    System.out.printf("  Min:            %d%n", minLatency);
    System.out.printf("  Avg:            %.0f%n", avgLatency);
    System.out.printf("  Max:            %d%n", maxLatency);
    System.out.printf("  P50:            %d%n", p50);
    System.out.printf("  P95:            %d%n", p95);
    System.out.printf("  P99:            %d%n", p99);
    System.out.println("═══════════════════════════════════════════════════════════════");

    if (!errors.isEmpty()) {
      System.out.println();
      System.out.println("  ERRORS (first 5)");
      System.out.println("  ─────────────────────────────────────────────────────────────");
      for (int i = 0; i < Math.min(5, errors.size()); i++) {
        System.out.printf("  %d. %s%n", i + 1, errors.get(i));
      }
      if (errors.size() > 5) {
        System.out.printf("  ... and %d more errors%n", errors.size() - 5);
      }
    }
  }

  private long percentile(List<Long> sorted, double p) {
    if (sorted.isEmpty()) {
      return 0;
    }
    int idx = (int) ((sorted.size() - 1) * p);
    return sorted.get(idx);
  }

  private String getConfig(String sysProp, String envVar, String defaultValue) {
    String value = System.getProperty(sysProp);
    if (value == null || value.isEmpty()) {
      value = System.getenv(envVar);
    }
    if (value == null || value.isEmpty()) {
      value = defaultValue;
    }
    return value;
  }
}
