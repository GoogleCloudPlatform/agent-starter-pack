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

"""Converters between A2A Parts and LangChain message content."""

from __future__ import annotations

import logging
from typing import Any

from a2a.types import FilePart, FileWithBytes, FileWithUri, Part, TextPart

logger = logging.getLogger(__name__)


LangChainContent = str | list[str | dict[str, Any]]
LangChainContentDict = dict[str, Any]


def convert_a2a_part_to_langchain_content(part: Part) -> LangChainContentDict | str:
    """Convert an A2A Part to LangChain message content format."""

    root = part.root

    if isinstance(root, TextPart):
        return {"type": "text", "text": root.text}

    elif isinstance(root, FilePart):
        file_data = root.file
        mime_type = file_data.mime_type if hasattr(file_data, "mime_type") else None

        # Determine media type from mime_type
        media_type = "image"  # default
        if mime_type:
            if mime_type.startswith("audio/"):
                media_type = "audio"
            elif mime_type.startswith("video/"):
                media_type = "video"

        if isinstance(file_data, FileWithUri):
            return {"type": media_type, "url": file_data.uri}
        else:
            # Base64 data should already be encoded
            return {
                "type": media_type,
                "base64": file_data.bytes,
                "mime_type": mime_type or "application/octet-stream",
            }

    else:
        import json

        data_str = json.dumps(root.data, indent=2)
        return {"type": "text", "text": f"[Structured Data]\n{data_str}"}


def convert_langchain_content_to_a2a_part(content: Any) -> Part:
    """Convert LangChain message content to an A2A Part."""

    if isinstance(content, str):
        return Part(root=TextPart(text=content))

    if isinstance(content, dict):
        content_type = content.get("type")

        if content_type == "text":
            text = content.get("text", "")
            return Part(root=TextPart(text=text))

        elif content_type in ("image", "audio", "video"):
            # Handle URL-based media
            if "url" in content:
                return Part(root=FilePart(file=FileWithUri(uri=content["url"])))

            # Handle base64-encoded media
            elif "base64" in content:
                mime_type = content.get("mime_type")
                return Part(
                    root=FilePart(
                        file=FileWithBytes(bytes=content["base64"], mime_type=mime_type)
                    )
                )

            # Handle file_id-based media
            elif "file_id" in content:
                return Part(
                    root=FilePart(file=FileWithUri(uri=f"file://{content['file_id']}"))
                )

        else:
            import json

            text = json.dumps(content)
            logger.warning(f"Unknown content type '{content_type}', converting to text")
            return Part(root=TextPart(text=text))

    logger.warning(f"Unknown content type: {type(content)}, converting to text")
    return Part(root=TextPart(text=str(content)))


def convert_a2a_parts_to_langchain_content(parts: list[Part]) -> LangChainContent:
    """Convert a list of A2A Parts to LangChain message content."""

    if not parts:
        return ""

    converted: list[str | dict[str, Any]] = []
    for part in parts:
        result = convert_a2a_part_to_langchain_content(part)
        converted.append(result)

    if len(converted) == 1 and isinstance(converted[0], str):
        return converted[0]

    return converted


def convert_langchain_content_to_a2a_parts(content: LangChainContent) -> list[Part]:
    """Convert LangChain message content to a list of A2A Parts."""

    if isinstance(content, str):
        return [Part(root=TextPart(text=content))]

    result: list[Part] = []
    for item in content:
        result.append(convert_langchain_content_to_a2a_part(item))
    return result
