# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess
import sys


def test_namespace_package_compat(tmp_path):
    """
    The ``google`` namespace package should not be masked
    by the presence of ``google-auth``.
    """
    google = tmp_path / "google"
    google.mkdir()
    google.joinpath("othermod.py").write_text("")
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    cmd = [sys.executable, "-m", "google.othermod"]
    subprocess.check_call(cmd, env=env)
