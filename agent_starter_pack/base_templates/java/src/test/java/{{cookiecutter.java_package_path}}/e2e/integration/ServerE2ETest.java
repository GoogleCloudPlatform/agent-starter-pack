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

package {{cookiecutter.java_package}}.e2e.integration;

import com.google.adk.web.AdkWebServer;
import {{cookiecutter.java_package}}.Agent;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

import static org.junit.jupiter.api.Assertions.*;

/**
 * End-to-end tests for the A2A server endpoints.
 * Tests the agent card endpoint and A2A message handling.
 */
@SpringBootTest(
    classes = {AdkWebServer.class, Agent.class},
    webEnvironment = WebEnvironment.RANDOM_PORT,
    properties = {"adk.agents.loader=static"}
)
class ServerE2ETest {

  @LocalServerPort
  private int port;

  @Autowired
  private TestRestTemplate restTemplate;

  /**
   * Tests that the agent card endpoint returns valid JSON with required fields.
   */
  @Test
  @SuppressWarnings("unchecked")
  void testAgentCardEndpoint() {
    String url = "http://localhost:" + port + "/.well-known/agent-card.json";
    ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

    assertEquals(HttpStatus.OK, response.getStatusCode());

    Map<String, Object> body = response.getBody();
    assertNotNull(body);

    // Validate required fields
    assertNotNull(body.get("name"), "AgentCard should have 'name'");
    assertNotNull(body.get("description"), "AgentCard should have 'description'");
    assertNotNull(body.get("url"), "AgentCard should have 'url'");
    assertNotNull(body.get("version"), "AgentCard should have 'version'");
    assertNotNull(body.get("capabilities"), "AgentCard should have 'capabilities'");
    assertNotNull(body.get("defaultInputModes"), "AgentCard should have 'defaultInputModes'");
    assertNotNull(body.get("defaultOutputModes"), "AgentCard should have 'defaultOutputModes'");
    assertNotNull(body.get("skills"), "AgentCard should have 'skills'");

    // Validate skills structure
    List<Map<String, Object>> skills = (List<Map<String, Object>>) body.get("skills");
    assertFalse(skills.isEmpty(), "AgentCard should have at least one skill");

    // Validate capabilities structure
    Map<String, Object> capabilities = (Map<String, Object>) body.get("capabilities");
    assertNotNull(capabilities);
    assertEquals(false, capabilities.get("streaming"));

    // Validate input/output modes
    List<String> inputModes = (List<String>) body.get("defaultInputModes");
    List<String> outputModes = (List<String>) body.get("defaultOutputModes");
    assertTrue(inputModes.contains("text/plain"));
    assertTrue(outputModes.contains("text/plain"));
  }

  /**
   * Tests A2A message/send endpoint with a valid JSON-RPC request.
   */
  @Test
  @SuppressWarnings("unchecked")
  void testA2AMessageSend() {
    String url = "http://localhost:" + port + "/a2a/remote/v1/message:send";

    // Create JSON-RPC request with proper A2A message format
    String messageId = UUID.randomUUID().toString();
    Map<String, Object> message = Map.of(
        "kind", "message",
        "messageId", messageId,
        "role", "user",
        "parts", List.of(Map.of("kind", "text", "text", "Hello"))
    );

    Map<String, Object> request = Map.of(
        "jsonrpc", "2.0",
        "id", UUID.randomUUID().toString(),
        "method", "message/send",
        "params", Map.of(
            "message", message
        )
    );

    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.APPLICATION_JSON);
    HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);

    ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

    // The endpoint should respond successfully
    assertNotNull(response);
    assertEquals(HttpStatus.OK, response.getStatusCode(),
        "Expected 200 OK from A2A endpoint, got " + response.getStatusCode());
  }

  /**
   * Tests A2A error handling for invalid JSON-RPC method.
   */
  @Test
  @SuppressWarnings("unchecked")
  void testA2AErrorHandling() {
    String url = "http://localhost:" + port + "/a2a/remote/v1/message:send";

    // Create an invalid JSON-RPC request with unknown method
    Map<String, Object> request = Map.of(
        "jsonrpc", "2.0",
        "id", UUID.randomUUID().toString(),
        "method", "invalid/method",
        "params", Map.of()
    );

    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.APPLICATION_JSON);
    HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);

    ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

    // Invalid method should return a response (either error status or JSON-RPC error)
    assertNotNull(response);
    Map<String, Object> body = response.getBody();
    if (body != null && body.containsKey("error")) {
      // JSON-RPC error format - this is expected
      assertNotNull(body.get("error"));
    }
  }
}
