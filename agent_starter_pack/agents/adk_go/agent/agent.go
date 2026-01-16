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

// Package agent contains the root agent implementation.
package agent

import (
	"context"

	"google.golang.org/genai"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model/gemini"
	"google.golang.org/adk/tool"
	"google.golang.org/adk/tool/functiontool"
)

// GetWeatherArgs defines the input for the get_weather tool.
type GetWeatherArgs struct {
	City string `json:"city" jsonschema:"City name to get weather for"`
}

// GetWeatherResult defines the output for the get_weather tool.
type GetWeatherResult struct {
	Weather string `json:"weather"`
}

// GetWeather returns mock weather data for a city.
func GetWeather(_ tool.Context, args GetWeatherArgs) (GetWeatherResult, error) {
	return GetWeatherResult{
		Weather: "It's sunny and 72°F in " + args.City,
	}, nil
}

// NewRootAgent creates and returns the root agent with all configured tools.
func NewRootAgent(ctx context.Context) (agent.Agent, error) {
	model, err := gemini.NewModel(ctx, "gemini-2.5-flash", &genai.ClientConfig{
		Backend: genai.BackendVertexAI,
	})
	if err != nil {
		return nil, err
	}

	weatherTool, err := functiontool.New(functiontool.Config{
		Name:        "get_weather",
		Description: "Get the current weather for a city.",
	}, GetWeather)
	if err != nil {
		return nil, err
	}

	rootAgent, err := llmagent.New(llmagent.Config{
		Name:        "{{cookiecutter.project_name}}",
		Model:       model,
		Description: "A helpful AI assistant.",
		Instruction: "You are a helpful AI assistant designed to provide accurate and useful information.",
		Tools:       []tool.Tool{weatherTool},
	})
	if err != nil {
		return nil, err
	}

	return rootAgent, nil
}
