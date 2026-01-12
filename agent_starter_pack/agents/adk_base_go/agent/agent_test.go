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

package agent

import (
	"strings"
	"testing"
)

func TestGetWeather(t *testing.T) {
	tests := []struct {
		name     string
		city     string
		wantCity string
	}{
		{
			name:     "San Francisco",
			city:     "San Francisco",
			wantCity: "San Francisco",
		},
		{
			name:     "New York",
			city:     "New York",
			wantCity: "New York",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Pass nil for tool.Context since GetWeather doesn't use it
			result, err := GetWeather(nil, GetWeatherArgs{City: tt.city})
			if err != nil {
				t.Fatalf("GetWeather() error = %v", err)
			}
			if !strings.Contains(result.Weather, tt.wantCity) {
				t.Errorf("GetWeather() = %v, want city %v in response", result.Weather, tt.wantCity)
			}
		})
	}
}
