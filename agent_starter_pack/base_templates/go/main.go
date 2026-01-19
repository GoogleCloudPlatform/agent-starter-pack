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

package main

import (
	"context"
	"log"
	"os"

	"{{cookiecutter.project_name}}/agent"

	cloudtrace "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"github.com/joho/godotenv"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"

	adkagent "google.golang.org/adk/agent"
	"google.golang.org/adk/cmd/launcher"
	"google.golang.org/adk/cmd/launcher/full"
	"google.golang.org/adk/session"
)

func main() {
	// Load .env file if present (local development only, ignored in production)
	_ = godotenv.Load(".env")

	ctx := context.Background()

	// Set up telemetry exporter with service resource
	res, _ := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceName("{{cookiecutter.project_name}}"),
		),
	)

	// Set up Cloud Trace - try ADC first, then env var
	var tp *sdktrace.TracerProvider
	exporter, err := cloudtrace.New()
	if err != nil {
		if projectID := os.Getenv("GOOGLE_CLOUD_PROJECT"); projectID != "" {
			exporter, err = cloudtrace.New(cloudtrace.WithProjectID(projectID))
		}
	}
	if err != nil {
		log.Printf("Warning: Cloud Trace disabled: %v", err)
	} else {
		tp = sdktrace.NewTracerProvider(
			sdktrace.WithBatcher(exporter),
			sdktrace.WithResource(res),
		)
		log.Println("Telemetry: Cloud Trace enabled")
	}
	if tp != nil {
		otel.SetTracerProvider(tp)
		// Set up W3C trace context propagation for linked spans
		otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
			propagation.TraceContext{},
			propagation.Baggage{},
		))
	}

	rootAgent, err := agent.NewRootAgent(ctx)
	if err != nil {
		log.Fatalf("Failed to create agent: %v", err)
	}

	config := &launcher.Config{
		AgentLoader:    adkagent.NewSingleLoader(rootAgent),
		SessionService: session.InMemoryService(),
	}

	args := os.Args[1:]
	// Inject -a2a_agent_url flag after "a2a" sublauncher for correct agent card URL
	// Uses APP_URL env var if set, otherwise defaults to localhost:8000 for local dev
	appURL := os.Getenv("APP_URL")
	if appURL == "" {
		appURL = "http://localhost:8000"
	}

	var newArgs []string
	for _, arg := range args {
		newArgs = append(newArgs, arg)
		if arg == "a2a" {
			newArgs = append(newArgs, "-a2a_agent_url", appURL)
		}
		if arg == "webui" {
			newArgs = append(newArgs, "-api_server_address", appURL+"/api")
		}
	}
	args = newArgs

	l := full.NewLauncher()
	if err = l.Execute(ctx, config, args); err != nil {
		log.Fatalf("Run failed: %v\n\n%s", err, l.CommandLineSyntax())
	}
}
