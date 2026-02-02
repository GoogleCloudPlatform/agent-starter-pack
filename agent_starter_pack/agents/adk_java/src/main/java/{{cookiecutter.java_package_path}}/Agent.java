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

import com.google.adk.agents.BaseAgent;
import com.google.adk.agents.LlmAgent;
import com.google.adk.tools.Annotations.Schema;
import com.google.adk.tools.FunctionTool;
import com.google.adk.web.AgentLoader;
import com.google.adk.web.AgentStaticLoader;
import com.google.adk.webservice.A2ARemoteConfiguration;
import io.a2a.spec.AgentCapabilities;
import io.a2a.spec.AgentCard;
import io.a2a.spec.AgentSkill;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Agent configuration class that defines the root LLM agent and its tools.
 */
@Configuration
@Import(A2ARemoteConfiguration.class)
@ComponentScan(basePackages = "{{cookiecutter.java_package}}")
public class Agent {

  public static final LlmAgent ROOT_AGENT =
      LlmAgent.builder()
          .name("{{cookiecutter.project_name}}")
          .model("gemini-3-flash-preview")
          .description("A helpful AI assistant that can provide weather information.")
          .instruction(
              "You are a helpful assistant that can provide weather information. "
              + "When asked about weather, use the get_weather tool. "
              + "Be friendly and concise in your responses.")
          .tools(FunctionTool.create(Agent.class, "getWeather"))
          .build();

  @Bean
  public BaseAgent rootAgent() {
    return ROOT_AGENT;
  }

  @Bean
  public AgentLoader agentLoader() {
    return new AgentStaticLoader(ROOT_AGENT);
  }

  /**
   * Get weather information for a city.
   *
   * @param city The city to get weather for
   * @return A map containing the weather status and report
   */
  public static Map<String, String> getWeather(
      @Schema(name = "city", description = "The city to get weather for")
      String city) {
    return Map.of(
        "status", "success",
        "report", "The weather in " + city + " is sunny with a high of 75°F.");
  }

  /**
   * REST controller that exposes the agent card for A2A discovery.
   */
  @RestController
  public static class AgentCardController {

    @Value("${APP_URL:http://localhost:8080}")
    private String appUrl;

    /**
     * Returns the agent card describing this agent's capabilities.
     *
     * @return The agent card for A2A discovery
     */
    @GetMapping("/.well-known/agent-card.json")
    public AgentCard getAgentCard() {
      List<AgentSkill> skills = ROOT_AGENT.tools().stream()
          .map(tool -> new AgentSkill.Builder()
              .id(ROOT_AGENT.name() + "-" + tool.name())
              .name(tool.name())
              .description(tool.description())
              .tags(List.of())
              .build())
          .toList();

      return new AgentCard.Builder()
          .name(ROOT_AGENT.name())
          .description(ROOT_AGENT.description())
          .url(appUrl + "/a2a/remote/v1/message:send")
          .version("1.0.0")
          .capabilities(new AgentCapabilities.Builder().streaming(false).build())
          .defaultInputModes(List.of("text/plain"))
          .defaultOutputModes(List.of("text/plain"))
          .skills(skills)
          .build();
    }
  }
}
