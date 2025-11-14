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

"""Converters for A2A and LangChain types."""

from .part_converter import (
    convert_a2a_parts_to_langchain_content,
    convert_langchain_content_to_a2a_parts,
)

__all__ = [
    "convert_a2a_parts_to_langchain_content",
    "convert_langchain_content_to_a2a_parts",
]
