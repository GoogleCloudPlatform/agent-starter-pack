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

from .datastores import DATASTORE_TYPES, get_datastore_info
from .gcp import verify_credentials
from .logging import handle_cli_error
from .template import (
    get_available_agents,
    get_deployment_targets,
    get_template_path,
    load_template_config,
    process_template,
    prompt_datastore_selection,
    prompt_deployment_target,
)
from .version import display_update_message

__all__ = [
    "DATASTORE_TYPES",
    "display_update_message",
    "get_available_agents",
    "get_datastore_info",
    "get_deployment_targets",
    "get_template_path",
    "handle_cli_error",
    "load_template_config",
    "process_template",
    "prompt_datastore_selection",
    "prompt_deployment_target",
    "verify_credentials",
]
