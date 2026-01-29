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
import com.google.adk.webservice.A2ARemoteConfiguration;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@Configuration
@Import(A2ARemoteConfiguration.class)
@ComponentScan(basePackages = "{{cookiecutter.java_package}}")
public class Agent {

    public static final BaseAgent ROOT_AGENT =
        LlmAgent.builder()
            .name("{{cookiecutter.project_name}}_agent")
            .model("gemini-3-flash-preview")
            .description("A helpful AI assistant that can provide weather information.")
            .instruction(
                "You are a helpful assistant that can provide weather information. "
                + "When asked about weather, use the get_weather tool. "
                + "Be friendly and concise in your responses.")
            .tools(FunctionTool.create(Agent.class, "getWeather"))
            .build();

    /** Exposes ROOT_AGENT as a Spring bean for A2A protocol support. */
    @Bean
    public BaseAgent rootAgent() {
        return ROOT_AGENT;
    }

    public static Map<String, String> getWeather(
        @Schema(name = "city", description = "The city to get weather for")
        String city) {
        return Map.of(
            "status", "success",
            "report", "The weather in " + city + " is sunny with a high of 75°F.");
    }

    @RestController
    public static class AgentCardController {

        @Value("${APP_URL:http://localhost:8080}")
        private String appUrl;

        @GetMapping("/.well-known/agent-card.json")
        public Map<String, Object> getAgentCard() {
            return Map.of(
                "name", ROOT_AGENT.name(),
                "description", ROOT_AGENT.description(),
                "url", appUrl + "/a2a/remote/v1",
                "version", "1.0.0",
                "capabilities", Map.of("streaming", false),
                "defaultInputModes", List.of("text/plain"),
                "defaultOutputModes", List.of("application/json")
            );
        }
    }
}
