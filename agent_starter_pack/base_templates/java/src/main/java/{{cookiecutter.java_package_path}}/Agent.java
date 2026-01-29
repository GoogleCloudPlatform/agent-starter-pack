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
import com.google.adk.webservice.A2ARemoteConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;

/**
 * Agent implementation.
 * This is a placeholder and will be overridden by the specific agent template.
 *
 * <p>Includes A2A protocol support via Spring configuration.
 * A2A endpoint: /a2a/remote/v1/message:send
 */
@Configuration
@Import(A2ARemoteConfiguration.class)
public class Agent {

    public static final BaseAgent ROOT_AGENT;

    static {
        throw new UnsupportedOperationException(
            "Agent not implemented - this file should be overridden by the agent template");
    }

    /**
     * Provides the root agent as a Spring bean for A2A protocol support.
     */
    @Bean
    public BaseAgent rootAgent() {
        return ROOT_AGENT;
    }
}
