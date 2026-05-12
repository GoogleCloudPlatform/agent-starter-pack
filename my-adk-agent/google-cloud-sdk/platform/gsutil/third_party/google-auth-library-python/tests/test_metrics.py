# Copyright 2014 Google Inc.
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

import platform

import mock

from google.auth import metrics
from google.auth import version


def test_add_metric_header():
    headers = {}
    metrics.add_metric_header(headers, None)
    assert headers == {}

    headers = {"x-goog-api-client": "foo"}
    metrics.add_metric_header(headers, "bar")
    assert headers == {"x-goog-api-client": "foo bar"}

    headers = {}
    metrics.add_metric_header(headers, "bar")
    assert headers == {"x-goog-api-client": "bar"}


@mock.patch.object(platform, "python_version", return_value="3.7")
def test_versions(mock_python_version):
    version_save = version.__version__
    version.__version__ = "1.1"
    assert metrics.python_and_auth_lib_version() == "gl-python/3.7 auth/1.1"
    version.__version__ = version_save


@mock.patch(
    "google.auth.metrics.python_and_auth_lib_version",
    return_value="gl-python/3.7 auth/1.1",
)
def test_metric_values(mock_python_and_auth_lib_version):
    assert (
        metrics.token_request_access_token_mds()
        == "gl-python/3.7 auth/1.1 auth-request-type/at cred-type/mds"
    )
    assert (
        metrics.token_request_id_token_mds()
        == "gl-python/3.7 auth/1.1 auth-request-type/it cred-type/mds"
    )
    assert (
        metrics.token_request_access_token_impersonate()
        == "gl-python/3.7 auth/1.1 auth-request-type/at cred-type/imp"
    )
    assert (
        metrics.token_request_id_token_impersonate()
        == "gl-python/3.7 auth/1.1 auth-request-type/it cred-type/imp"
    )
    assert (
        metrics.token_request_access_token_sa_assertion()
        == "gl-python/3.7 auth/1.1 auth-request-type/at cred-type/sa"
    )
    assert (
        metrics.token_request_id_token_sa_assertion()
        == "gl-python/3.7 auth/1.1 auth-request-type/it cred-type/sa"
    )
    assert metrics.token_request_user() == "gl-python/3.7 auth/1.1 cred-type/u"
    assert metrics.mds_ping() == "gl-python/3.7 auth/1.1 auth-request-type/mds"
    assert metrics.reauth_start() == "gl-python/3.7 auth/1.1 auth-request-type/re-start"
    assert (
        metrics.reauth_continue() == "gl-python/3.7 auth/1.1 auth-request-type/re-cont"
    )


@mock.patch(
    "google.auth.metrics.python_and_auth_lib_version",
    return_value="gl-python/3.7 auth/1.1",
)
def test_byoid_metric_header(mock_python_and_auth_lib_version):
    metrics_options = {}
    assert (
        metrics.byoid_metrics_header(metrics_options)
        == "gl-python/3.7 auth/1.1 google-byoid-sdk"
    )
    metrics_options["testKey"] = "testValue"
    assert (
        metrics.byoid_metrics_header(metrics_options)
        == "gl-python/3.7 auth/1.1 google-byoid-sdk testKey/testValue"
    )
