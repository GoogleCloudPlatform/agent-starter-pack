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
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;

import java.util.Map;

/**
 * Agent implementation with weather tool.
 *
 * <p>Includes A2A protocol support via Spring configuration.
 * A2A endpoint: /a2a/remote/v1/message:send
 */
@Configuration
@Import(A2ARemoteConfiguration.class)
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

    /**
     * Provides the root agent as a Spring bean for A2A protocol support.
     */
    @Bean
    public BaseAgent rootAgent() {
        return ROOT_AGENT;
    }

    /**
     * Get the current weather for a city.
     *
     * @param city The city to get weather for
     * @return A map containing status and weather report
     */
    public static Map<String, String> getWeather(
        @Schema(name = "city", description = "The city to get weather for")
        String city) {
        return Map.of(
            "status", "success",
            "report", "The weather in " + city + " is sunny with a high of 75°F.");
    }
}
