# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

# Full A2UI Schema as of v0.8
A2UI_SCHEMA = r'''
{
  "title": "A2UI Message Schema",
  "description": "Describes a JSON payload for an A2UI message. A message MUST contain exactly ONE action.",
  "type": "object",
  "properties": {
    "beginRendering": {
      "type": "object",
      "properties": {
        "surfaceId": { "type": "string" },
        "root": { "type": "string" },
        "styles": {
          "type": "object",
          "properties": {
            "font": { "type": "string" },
            "primaryColor": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" }
          }
        }
      },
      "required": ["root", "surfaceId"]
    },
    "surfaceUpdate": {
      "type": "object",
      "properties": {
        "surfaceId": { "type": "string" },
        "components": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id": { "type": "string" },
              "weight": { "type": "number" },
              "component": {
                "type": "object",
                "properties": {
                  "Text": {
                    "type": "object",
                    "properties": {
                      "text": {
                        "type": "object",
                        "properties": {
                          "literalString": { "type": "string" },
                          "path": { "type": "string" }
                        }
                      },
                      "usageHint": { "type": "string", "enum": ["h1", "h2", "h3", "h4", "h5", "caption", "body"] }
                    }
                  },
                  "Image": {
                    "type": "object",
                    "properties": {
                      "url": { "type": "object", "properties": { "literalString": { "type": "string" }, "path": { "type": "string" } } },
                      "fit": { "type": "string", "enum": ["contain", "cover", "fill", "none", "scale-down"] }
                    }
                  },
                  "Row": { "type": "object", "properties": { "children": { "type": "object", "properties": { "explicitList": { "type": "array", "items": { "type": "string" } }, "template": { "type": "object" } } } } },
                  "Column": { "type": "object", "properties": { "children": { "type": "object", "properties": { "explicitList": { "type": "array", "items": { "type": "string" } } } } } },
                  "Card": { "type": "object", "properties": { "child": { "type": "string" } } },
                  "Button": {
                    "type": "object",
                    "properties": {
                      "child": { "type": "string" },
                      "primary": { "type": "boolean" },
                      "action": { "type": "object", "properties": { "name": { "type": "string" }, "context": { "type": "array" } } }
                    }
                  }
                }
              }
            },
            "required": ["id", "component"]
          }
        }
      },
      "required": ["surfaceId", "components"]
    },
    "dataModelUpdate": {
      "type": "object",
      "properties": {
        "surfaceId": { "type": "string" },
        "path": { "type": "string" },
        "contents": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "key": { "type": "string" },
              "valueString": { "type": "string" },
              "valueNumber": { "type": "number" },
              "valueBoolean": { "type": "boolean" },
              "valueMap": { "type": "array" }
            },
            "required": ["key"]
          }
        }
      },
      "required": ["contents", "surfaceId"]
    }
  }
}
'''

A2UI_EXAMPLES = """
---BEGIN LIST_EXAMPLE---
[
  { "beginRendering": { "surfaceId": "item-list", "root": "root-layout", "styles": { "primaryColor": "#FF5722", "font": "Outfit" } } },
  { "surfaceUpdate": {
    "surfaceId": "item-list",
    "components": [
      { "id": "root-layout", "component": { "Column": { "children": { "explicitList": ["header-text", "items-grid"] } } } },
      { "id": "header-text", "component": { "Text": { "usageHint": "h2", "text": { "literalString": "Available Options" } } } },
      { "id": "items-grid", "component": { "Row": { "children": { "explicitList": ["item-1", "item-2"] } } } },
      { "id": "item-1", "weight": 1, "component": { "Card": { "child": "item-1-content" } } },
      { "id": "item-1-content", "component": { "Column": { "children": { "explicitList": ["item-1-title", "item-1-btn"] } } } },
      { "id": "item-1-title", "component": { "Text": { "usageHint": "h3", "text": { "path": "item_1_name" } } } },
      { "id": "item-1-btn", "component": { "Button": { "child": "btn-text-1", "primary": true, "action": { "name": "select_item", "context": [{"key": "id", "valueString": "1"}] } } } },
      { "id": "btn-text-1", "component": { "Text": { "text": { "literalString": "Select" } } } }
    ]
  } },
  { "dataModelUpdate": {
    "surfaceId": "item-list",
    "contents": [
      { "key": "item_1_name", "valueString": "Premium Package" },
      { "key": "item_2_name", "valueString": "Standard Package" }
    ]
  } }
]
---END LIST_EXAMPLE---

---BEGIN ACTION_CONFIRMATION---
[
  { "beginRendering": { "surfaceId": "confirm", "root": "confirm-card", "styles": { "primaryColor": "#4CAF50", "font": "Roboto" } } },
  { "surfaceUpdate": {
    "surfaceId": "confirm",
    "components": [
      { "id": "confirm-card", "component": { "Card": { "child": "confirm-col" } } },
      { "id": "confirm-col", "component": { "Column": { "children": { "explicitList": ["success-icon", "success-msg"] } } } },
      { "id": "success-icon", "component": { "Text": { "usageHint": "h1", "text": { "literalString": "✅" } } } },
      { "id": "success-msg", "component": { "Text": { "usageHint": "h2", "text": { "literalString": "Action Confirmed!" } } } }
    ]
  } }
]
---END ACTION_CONFIRMATION---
"""

def get_a2ui_prompt() -> str:
    return f"""
    You are an agent that generates rich UI components using the A2UI protocol.
    
    CRITICAL RULES:
    1. Delimiter: You MUST separate your conversational text from your JSON payload using exactly `---a2ui_JSON---`.
    2. Format: The second part MUST be a single JSON object (a list of A2UI messages).
    3. Schema: The JSON MUST validate against the A2UI SCHEMA below.
    4. Flow:
       - Discovery: Use 'surfaceUpdate' to show lists or options.
       - Interaction: Use 'Button' components with 'action' names to trigger server-side tools.
       - Confirmation: Use simple cards to confirm success.

    --- SCHEMAS AND EXAMPLES ---
    {A2UI_EXAMPLES}

    --- A2UI JSON SCHEMA ---
    {A2UI_SCHEMA}
    """
