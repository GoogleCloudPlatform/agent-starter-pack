# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# mypy: disable-error-code="assignment"
import os
from typing import Any

import google.auth
from google import genai
from google.adk.events.event import Event
from google.genai.types import Content, GenerateContentConfig, HttpOptions, Part

SYS_INSTRUCTION = """Given a list of messages between a human and AI, come up with a short and relevant title for the conversation. Use up to 10 words. The title needs to be concise.
Examples:
**Input:**
```
Human: hi, what is the best italian dish?
AI: That's a tough one! Italy has so many amazing dishes, it's hard to pick just one "best." To help me give you a great suggestion, tell me a little more about what you're looking for.
```
**Output:** Best italian dish

**Input:**

```
Human: How to fix a broken laptop screen?
AI: Fixing a broken laptop screen can be tricky and often requires professional help. However, there are a few things you can try at home before resorting to a repair shop.
```

**Output:** Fixing a broken laptop screen

**Input:**

```
Human: Can you write me a poem about the beach?
AI: As the sun dips down below the horizon
And the waves gently kiss the shore,
I sit here and watch the ocean
And feel its power evermore.
```

**Output:** Poem about the beach

**Input:**

```
Human: What's the best way to learn to code?
AI: There are many ways to learn to code, and the best method for you will depend on your learning style and goals.
```

**Output:** How to learn to code

If there's not enough context in the conversation to create a meaningful title, create a generic title like "New Conversation", or "A simple greeting".

"""


class TitleGenerator:
    """Generates concise titles for conversations using Gemini model."""

    def __init__(self) -> None:
        _, project_id = google.auth.default()

        self.client = genai.Client(
            http_options=HttpOptions(api_version="v1"),
            vertexai=True,
            project=project_id,
            location=os.getenv("LOCATION", "us-central1"),
        )

    def summarize(self, events: list[Event]) -> str:
        """Generates a title based on a list of conversation events."""
        contents = []
        # Extract text content from each event and add it to the contents list
        for event in events:
            if event.get("content") and event["content"].get("parts"):
                text_parts = [
                    part.get("text", "")
                    for part in event["content"]["parts"]
                    if part.get("text")
                ]
                text_content = "\n".join(text_parts)
                if text_content.strip():
                    contents.append(
                        Content(
                            role=event["content"].get("role", "user"),
                            parts=[Part.from_text(text=text_content)],
                        )
                    )
        contents.append(
            Content(
                role="user",
                parts=[
                    Part.from_text(text="End of conversation - Create one single title")
                ],
            )
        )
        response = self.client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=SYS_INSTRUCTION,
                max_output_tokens=10,
                temperature=0,
            ),
        ).text
        return response


class DummySummarizer:
    """A simple summarizer that returns a fixed string."""

    def __init__(self) -> None:
        """Initialize the dummy summarizer."""
        pass

    def summarize(self, **kwargs: Any) -> str:
        """Return a simple summary string regardless of input."""
        return "Conversation"
