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

package {{cookiecutter.java_package}};

import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for Agent.
 */
class AgentTest {

    @Test
    void testGetWeatherReturnsCityName() {
        Map<String, String> result = Agent.getWeather("San Francisco");

        assertNotNull(result);
        assertEquals("success", result.get("status"));
        assertTrue(result.get("report").contains("San Francisco"));
    }

    @Test
    void testGetWeatherWithDifferentCity() {
        Map<String, String> result = Agent.getWeather("New York");

        assertNotNull(result);
        assertEquals("success", result.get("status"));
        assertTrue(result.get("report").contains("New York"));
    }

    @Test
    void testAgentExists() {
        assertNotNull(Agent.ROOT_AGENT);
    }

    @Test
    @SuppressWarnings("unchecked")
    void testAgentCardResponse() throws Exception {
        // Create controller and inject appUrl via reflection
        Agent.AgentCardController controller = new Agent.AgentCardController();
        Field appUrlField = Agent.AgentCardController.class.getDeclaredField("appUrl");
        appUrlField.setAccessible(true);
        appUrlField.set(controller, "http://localhost:8080");

        // Get the AgentCard response
        Map<String, Object> agentCard = controller.getAgentCard();

        // Validate required fields exist
        assertNotNull(agentCard.get("name"), "AgentCard should have 'name'");
        assertNotNull(agentCard.get("description"), "AgentCard should have 'description'");
        assertNotNull(agentCard.get("url"), "AgentCard should have 'url'");
        assertNotNull(agentCard.get("version"), "AgentCard should have 'version'");
        assertNotNull(agentCard.get("capabilities"), "AgentCard should have 'capabilities'");
        assertNotNull(agentCard.get("defaultInputModes"), "AgentCard should have 'defaultInputModes'");
        assertNotNull(agentCard.get("defaultOutputModes"), "AgentCard should have 'defaultOutputModes'");

        // Validate field values
        assertEquals(Agent.ROOT_AGENT.name(), agentCard.get("name"));
        assertEquals(Agent.ROOT_AGENT.description(), agentCard.get("description"));
        assertEquals("http://localhost:8080/a2a/remote/v1", agentCard.get("url"));
        assertEquals("1.0.0", agentCard.get("version"));

        // Validate capabilities structure
        Map<String, Object> capabilities = (Map<String, Object>) agentCard.get("capabilities");
        assertEquals(false, capabilities.get("streaming"));

        // Validate input/output modes
        List<String> inputModes = (List<String>) agentCard.get("defaultInputModes");
        List<String> outputModes = (List<String>) agentCard.get("defaultOutputModes");
        assertTrue(inputModes.contains("text/plain"));
        assertTrue(outputModes.contains("application/json"));
    }
}
