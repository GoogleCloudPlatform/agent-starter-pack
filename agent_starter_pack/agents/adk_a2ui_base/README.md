# ADK with A2UI Protocol: Base Agent Example

<p align="center">
  <img src="https://github.com/GoogleCloudPlatform/agent-starter-pack/blob/main/docs/images/adk_logo.png?raw=true" width="200" alt="ADK Logo" style="margin-right: 40px; vertical-align: middle;">
  <img src="https://raw.githubusercontent.com/google/A2UI/main/docs/assets/a2ui-logo.png" width="200" alt="A2UI Logo" style="vertical-align: middle;">
</p>

This template provides a **production-ready foundation** for building agents that "speak UI" using the **[A2UI (Agent-to-User Interface)](https://github.com/google/A2UI)** protocol.

## 🚀 Does it actually generate UI?
**Yes.** This agent is specifically tuned to output a two-part response:
1.  **Conversational Text**: A standard text greeting or explanation.
2.  **A2UI JSON Payload**: A structured description of UI surfaces (Cards, Rows, Columns, Buttons) that a compatible client renderer (like AG UI or A2UI's Flutter/Web renderers) will transform into native widgets.

## 💡 Sample Queries & Flows

### 1. Discovery Flow
**Query:** "Show me what packages you have available"
- **Agent Action:** Calls `list_items(category="packages")`.
- **UI Output:** Generates a `surfaceUpdate` with a grid/list of package cards, each featuring a "Select" button.

### 2. Interaction Flow
**Trigger:** User clicks a "Select" button or says "I'll take the Premium Package".
- **Agent Action:** Calls `confirm_selection(item_id="1")`.
- **UI Output:** Generates an `ACTION_CONFIRMATION` surface showing a success checkmark.

### 3. Advanced Gen-UI Patterns
The agent's A2UI logic supports dynamic composition beyond fixed templates. Try these:
- **Visual Styler:** "Show me the packages but use a dark theme with blue accents and a Roboto font."
- **Comparison View:** "Compare the Premium and Standard packages in a side-by-side view."
- **Rich Interaction:** "Sign me up for package #1" (Triggers server-side confirmation + success card).

## 🛠️ Testing the Template

Since A2UI requires a client-side renderer to *see* the UI, you can test the **raw JSON generation** in the ADK Playground:

1.  Create the agent: `adk create my-app -a adk_a2ui_base`
2.  Start playground: `make playground`
3.  Ask: "Show me available packages"
4.  Verify the output contains the `---a2ui_JSON---` delimiter followed by a valid JSON array.

## 🏗️ Architecture: `a2ui_logic.py`
The core of this template resides in `app/a2ui_logic.py`, which defines:
- **The Protocol Schema**: Strictly enforces component hierarchy and properties.
- **Component Templates**: Pre-defined snippets (Row, Card, List) that the LLM can easily populate.
- **Prompt Engineering**: The logic required to ensure the LLM never "hallucinates" non-compliant JSON.

## Additional Resources
- **A2UI Project**: [GitHub](https://github.com/google/A2UI)
- **ADK Documentation**: [official documentation](https://google.github.io/adk-docs/)
