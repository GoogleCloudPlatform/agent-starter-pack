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

package {{cookiecutter.java_package}}.unit;

import {{cookiecutter.java_package}}.Agent;
import java.util.Map;
import org.junit.jupiter.api.Test;

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
}
