# Copyright 2018 Google Inc.
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

import copy
import datetime
import http.client as http_client
import json
import os

import mock
import pytest  # type: ignore

from google.auth import _helpers
from google.auth import crypt
from google.auth import exceptions
from google.auth import impersonated_credentials
from google.auth import transport
from google.auth.impersonated_credentials import Credentials
from google.oauth2 import credentials
from google.oauth2 import service_account

DATA_DIR = os.path.join(os.path.dirname(__file__), "", "data")

with open(os.path.join(DATA_DIR, "privatekey.pem"), "rb") as fh:
    PRIVATE_KEY_BYTES = fh.read()

SERVICE_ACCOUNT_JSON_FILE = os.path.join(DATA_DIR, "service_account.json")
IMPERSONATED_SERVICE_ACCOUNT_AUTHORIZED_USER_SOURCE_FILE = os.path.join(
    DATA_DIR, "impersonated_service_account_authorized_user_source.json"
)

ID_TOKEN_DATA = (
    "eyJhbGciOiJSUzI1NiIsImtpZCI6ImRmMzc1ODkwOGI3OTIyOTNhZDk3N2Ew"
    "Yjk5MWQ5OGE3N2Y0ZWVlY2QiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiJodHRwc"
    "zovL2Zvby5iYXIiLCJhenAiOiIxMDIxMDE1NTA4MzQyMDA3MDg1NjgiLCJle"
    "HAiOjE1NjQ0NzUwNTEsImlhdCI6MTU2NDQ3MTQ1MSwiaXNzIjoiaHR0cHM6L"
    "y9hY2NvdW50cy5nb29nbGUuY29tIiwic3ViIjoiMTAyMTAxNTUwODM0MjAwN"
    "zA4NTY4In0.redacted"
)
ID_TOKEN_EXPIRY = 1564475051

with open(SERVICE_ACCOUNT_JSON_FILE, "rb") as fh:
    SERVICE_ACCOUNT_INFO = json.load(fh)

with open(IMPERSONATED_SERVICE_ACCOUNT_AUTHORIZED_USER_SOURCE_FILE, "rb") as fh:
    IMPERSONATED_SERVICE_ACCOUNT_AUTHORIZED_USER_SOURCE_INFO = json.load(fh)

SIGNER = crypt.RSASigner.from_string(PRIVATE_KEY_BYTES, "1")
TOKEN_URI = "https://example.com/oauth2/token"

ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE = (
    "gl-python/3.7 auth/1.1 auth-request-type/at cred-type/imp"
)
ID_TOKEN_REQUEST_METRICS_HEADER_VALUE = (
    "gl-python/3.7 auth/1.1 auth-request-type/it cred-type/imp"
)


@pytest.fixture
def mock_donor_credentials():
    with mock.patch("google.oauth2._client.jwt_grant", autospec=True) as grant:
        grant.return_value = (
            "source token",
            _helpers.utcnow() + datetime.timedelta(seconds=500),
            {},
        )
        yield grant


@pytest.fixture
def mock_dwd_credentials():
    with mock.patch("google.oauth2._client.jwt_grant", autospec=True) as grant:
        grant.return_value = (
            "1/fFAGRNJasdfz70BzhT3Zg",
            _helpers.utcnow() + datetime.timedelta(seconds=500),
            {},
        )
        yield grant


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


@pytest.fixture
def mock_authorizedsession_sign():
    with mock.patch(
        "google.auth.transport.requests.AuthorizedSession.request", autospec=True
    ) as auth_session:
        data = {"keyId": "1", "signedBlob": "c2lnbmF0dXJl"}
        auth_session.return_value = MockResponse(data, http_client.OK)
        yield auth_session


@pytest.fixture
def mock_authorizedsession_idtoken():
    with mock.patch(
        "google.auth.transport.requests.AuthorizedSession.request", autospec=True
    ) as auth_session:
        data = {"token": ID_TOKEN_DATA}
        auth_session.return_value = MockResponse(data, http_client.OK)
        yield auth_session


class TestImpersonatedCredentials(object):

    SERVICE_ACCOUNT_EMAIL = "service-account@example.com"
    TARGET_PRINCIPAL = "impersonated@project.iam.gserviceaccount.com"
    TARGET_SCOPES = ["https://www.googleapis.com/auth/devstorage.read_only"]
    # DELEGATES: List[str] = []
    # Because Python 2.7:
    DELEGATES = []  # type: ignore
    LIFETIME = 3600
    SOURCE_CREDENTIALS = service_account.Credentials(
        SIGNER, SERVICE_ACCOUNT_EMAIL, TOKEN_URI
    )
    USER_SOURCE_CREDENTIALS = credentials.Credentials(token="ABCDE")
    IAM_ENDPOINT_OVERRIDE = (
        "https://us-east1-iamcredentials.googleapis.com/v1/projects/-"
        + "/serviceAccounts/{}:generateAccessToken".format(SERVICE_ACCOUNT_EMAIL)
    )

    def make_credentials(
        self,
        source_credentials=SOURCE_CREDENTIALS,
        lifetime=LIFETIME,
        target_principal=TARGET_PRINCIPAL,
        subject=None,
        iam_endpoint_override=None,
    ):

        return Credentials(
            source_credentials=source_credentials,
            target_principal=target_principal,
            target_scopes=self.TARGET_SCOPES,
            delegates=self.DELEGATES,
            lifetime=lifetime,
            subject=subject,
            iam_endpoint_override=iam_endpoint_override,
        )

    def test_from_impersonated_service_account_info(self):
        credentials = impersonated_credentials.Credentials.from_impersonated_service_account_info(
            IMPERSONATED_SERVICE_ACCOUNT_AUTHORIZED_USER_SOURCE_INFO
        )
        assert isinstance(credentials, impersonated_credentials.Credentials)

    def test_from_impersonated_service_account_info_with_invalid_source_credentials_type(
        self
    ):
        info = copy.deepcopy(IMPERSONATED_SERVICE_ACCOUNT_AUTHORIZED_USER_SOURCE_INFO)
        assert "source_credentials" in info
        # Set the source_credentials to an invalid type
        info["source_credentials"]["type"] = "invalid_type"
        with pytest.raises(exceptions.DefaultCredentialsError) as excinfo:
            impersonated_credentials.Credentials.from_impersonated_service_account_info(
                info
            )
        assert excinfo.match(
            "source credential of type {} is not supported".format("invalid_type")
        )

    def test_from_impersonated_service_account_info_with_invalid_impersonation_url(
        self
    ):
        info = copy.deepcopy(IMPERSONATED_SERVICE_ACCOUNT_AUTHORIZED_USER_SOURCE_INFO)
        info["service_account_impersonation_url"] = "invalid_url"
        with pytest.raises(exceptions.DefaultCredentialsError) as excinfo:
            impersonated_credentials.Credentials.from_impersonated_service_account_info(
                info
            )
        assert excinfo.match(r"Cannot extract target principal from")

    def test_get_cred_info(self):
        credentials = self.make_credentials()
        assert not credentials.get_cred_info()

        credentials._cred_file_path = "/path/to/file"
        assert credentials.get_cred_info() == {
            "credential_source": "/path/to/file",
            "credential_type": "impersonated credentials",
            "principal": "impersonated@project.iam.gserviceaccount.com",
        }

    def test_universe_domain_matching_source(self):
        source_credentials = service_account.Credentials(
            SIGNER, "some@email.com", TOKEN_URI, universe_domain="foo.bar"
        )
        credentials = self.make_credentials(source_credentials=source_credentials)
        assert credentials.universe_domain == "foo.bar"

    def test__make_copy_get_cred_info(self):
        credentials = self.make_credentials()
        credentials._cred_file_path = "/path/to/file"
        cred_copy = credentials._make_copy()
        assert cred_copy._cred_file_path == "/path/to/file"

    def test_make_from_user_credentials(self):
        credentials = self.make_credentials(
            source_credentials=self.USER_SOURCE_CREDENTIALS
        )
        assert not credentials.valid
        assert credentials.expired

    def test_default_state(self):
        credentials = self.make_credentials()
        assert not credentials.valid
        assert credentials.expired

    def test_make_from_service_account_self_signed_jwt(self):
        source_credentials = service_account.Credentials(
            SIGNER, self.SERVICE_ACCOUNT_EMAIL, TOKEN_URI, always_use_jwt_access=True
        )
        credentials = self.make_credentials(source_credentials=source_credentials)
        # test the source credential don't lose self signed jwt setting
        assert credentials._source_credentials._always_use_jwt_access
        assert credentials._source_credentials._jwt_credentials

    def make_request(
        self,
        data,
        status=http_client.OK,
        headers=None,
        side_effect=None,
        use_data_bytes=True,
    ):
        response = mock.create_autospec(transport.Response, instance=False)
        response.status = status
        response.data = _helpers.to_bytes(data) if use_data_bytes else data
        response.headers = headers or {}

        request = mock.create_autospec(transport.Request, instance=False)
        request.side_effect = side_effect
        request.return_value = response

        return request

    def test_token_usage_metrics(self):
        credentials = self.make_credentials()
        credentials.token = "token"
        credentials.expiry = None

        headers = {}
        credentials.before_request(mock.Mock(), None, None, headers)
        assert headers["authorization"] == "Bearer token"
        assert headers["x-goog-api-client"] == "cred-type/imp"

    @pytest.mark.parametrize("use_data_bytes", [True, False])
    def test_refresh_success(self, use_data_bytes, mock_donor_credentials):
        credentials = self.make_credentials(lifetime=None)
        token = "token"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body),
            status=http_client.OK,
            use_data_bytes=use_data_bytes,
        )

        with mock.patch(
            "google.auth.metrics.token_request_access_token_impersonate",
            return_value=ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE,
        ):
            credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired
        assert (
            request.call_args.kwargs["headers"]["x-goog-api-client"]
            == ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE
        )

    @pytest.mark.parametrize("use_data_bytes", [True, False])
    def test_refresh_with_subject_success(self, use_data_bytes, mock_dwd_credentials):
        credentials = self.make_credentials(subject="test@email.com", lifetime=None)

        response_body = {"signedJwt": "example_signed_jwt"}

        request = self.make_request(
            data=json.dumps(response_body),
            status=http_client.OK,
            use_data_bytes=use_data_bytes,
        )

        with mock.patch(
            "google.auth.metrics.token_request_access_token_impersonate",
            return_value=ACCESS_TOKEN_REQUEST_METRICS_HEADER_VALUE,
        ):
            credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired
        assert credentials.token == "1/fFAGRNJasdfz70BzhT3Zg"

    @pytest.mark.parametrize("use_data_bytes", [True, False])
    def test_refresh_success_nonGdu(self, use_data_bytes, mock_donor_credentials):
        source_credentials = service_account.Credentials(
            SIGNER, "some@email.com", TOKEN_URI, universe_domain="foo.bar"
        )
        credentials = self.make_credentials(
            lifetime=None, source_credentials=source_credentials
        )
        token = "token"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body),
            status=http_client.OK,
            use_data_bytes=use_data_bytes,
        )

        credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired
        # Confirm override endpoint used.
        request_kwargs = request.call_args[1]
        assert (
            request_kwargs["url"]
            == "https://iamcredentials.foo.bar/v1/projects/-/serviceAccounts/impersonated@project.iam.gserviceaccount.com:generateAccessToken"
        )

    @pytest.mark.parametrize("use_data_bytes", [True, False])
    def test_refresh_success_iam_endpoint_override(
        self, use_data_bytes, mock_donor_credentials
    ):
        credentials = self.make_credentials(
            lifetime=None, iam_endpoint_override=self.IAM_ENDPOINT_OVERRIDE
        )
        token = "token"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body),
            status=http_client.OK,
            use_data_bytes=use_data_bytes,
        )

        credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired
        # Confirm override endpoint used.
        request_kwargs = request.call_args[1]
        assert request_kwargs["url"] == self.IAM_ENDPOINT_OVERRIDE

    @pytest.mark.parametrize("time_skew", [150, -150])
    def test_refresh_source_credentials(self, time_skew):
        credentials = self.make_credentials(lifetime=None)

        # Source credentials is refreshed only if it is expired within
        # _helpers.REFRESH_THRESHOLD from now. We add a time_skew to the expiry, so
        # source credentials is refreshed only if time_skew <= 0.
        credentials._source_credentials.expiry = (
            _helpers.utcnow()
            + _helpers.REFRESH_THRESHOLD
            + datetime.timedelta(seconds=time_skew)
        )
        credentials._source_credentials.token = "Token"

        with mock.patch(
            "google.oauth2.service_account.Credentials.refresh", autospec=True
        ) as source_cred_refresh:
            expire_time = (
                _helpers.utcnow().replace(microsecond=0)
                + datetime.timedelta(seconds=500)
            ).isoformat("T") + "Z"
            response_body = {"accessToken": "token", "expireTime": expire_time}
            request = self.make_request(
                data=json.dumps(response_body), status=http_client.OK
            )

            credentials.refresh(request)

            assert credentials.valid
            assert not credentials.expired

            # Source credentials is refreshed only if it is expired within
            # _helpers.REFRESH_THRESHOLD
            if time_skew > 0:
                source_cred_refresh.assert_not_called()
            else:
                source_cred_refresh.assert_called_once()

    def test_refresh_failure_malformed_expire_time(self, mock_donor_credentials):
        credentials = self.make_credentials(lifetime=None)
        token = "token"

        expire_time = (_helpers.utcnow() + datetime.timedelta(seconds=500)).isoformat(
            "T"
        )
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body), status=http_client.OK
        )

        with pytest.raises(exceptions.RefreshError) as excinfo:
            credentials.refresh(request)

        assert excinfo.match(impersonated_credentials._REFRESH_ERROR)

        assert not credentials.valid
        assert credentials.expired

    def test_refresh_failure_unauthorzed(self, mock_donor_credentials):
        credentials = self.make_credentials(lifetime=None)

        response_body = {
            "error": {
                "code": 403,
                "message": "The caller does not have permission",
                "status": "PERMISSION_DENIED",
            }
        }

        request = self.make_request(
            data=json.dumps(response_body), status=http_client.UNAUTHORIZED
        )

        with pytest.raises(exceptions.RefreshError) as excinfo:
            credentials.refresh(request)

        assert excinfo.match(impersonated_credentials._REFRESH_ERROR)

        assert not credentials.valid
        assert credentials.expired

    def test_refresh_failure(self):
        credentials = self.make_credentials(lifetime=None)
        credentials.expiry = None
        credentials.token = "token"
        id_creds = impersonated_credentials.IDTokenCredentials(
            credentials, target_audience="audience"
        )

        response = mock.create_autospec(transport.Response, instance=False)
        response.status_code = http_client.UNAUTHORIZED
        response.json = mock.Mock(return_value="failed to get ID token")

        with mock.patch(
            "google.auth.transport.requests.AuthorizedSession.post",
            return_value=response,
        ):
            with pytest.raises(exceptions.RefreshError) as excinfo:
                id_creds.refresh(None)

        assert excinfo.match("Error getting ID token")

    def test_refresh_failure_http_error(self, mock_donor_credentials):
        credentials = self.make_credentials(lifetime=None)

        response_body = {}

        request = self.make_request(
            data=json.dumps(response_body), status=http_client.HTTPException
        )

        with pytest.raises(exceptions.RefreshError) as excinfo:
            credentials.refresh(request)

        assert excinfo.match(impersonated_credentials._REFRESH_ERROR)

        assert not credentials.valid
        assert credentials.expired

    def test_refresh_failure_subject_with_nondefault_domain(
        self, mock_donor_credentials
    ):
        source_credentials = service_account.Credentials(
            SIGNER, "some@email.com", TOKEN_URI, universe_domain="foo.bar"
        )
        credentials = self.make_credentials(
            source_credentials=source_credentials, subject="test@email.com"
        )

        expire_time = (_helpers.utcnow().replace(microsecond=0)).isoformat("T") + "Z"
        response_body = {"accessToken": "token", "expireTime": expire_time}
        request = self.make_request(
            data=json.dumps(response_body), status=http_client.OK
        )

        with pytest.raises(exceptions.GoogleAuthError) as excinfo:
            credentials.refresh(request)

        assert excinfo.match(
            "Domain-wide delegation is not supported in universes other "
            + "than googleapis.com"
        )

        assert not credentials.valid
        assert credentials.expired

    def test_expired(self):
        credentials = self.make_credentials(lifetime=None)
        assert credentials.expired

    def test_signer(self):
        credentials = self.make_credentials()
        assert isinstance(credentials.signer, impersonated_credentials.Credentials)

    def test_signer_email(self):
        credentials = self.make_credentials(target_principal=self.TARGET_PRINCIPAL)
        assert credentials.signer_email == self.TARGET_PRINCIPAL

    def test_service_account_email(self):
        credentials = self.make_credentials(target_principal=self.TARGET_PRINCIPAL)
        assert credentials.service_account_email == self.TARGET_PRINCIPAL

    def test_sign_bytes(self, mock_donor_credentials, mock_authorizedsession_sign):
        credentials = self.make_credentials(lifetime=None)
        expected_url = "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/impersonated@project.iam.gserviceaccount.com:signBlob"
        self._sign_bytes_helper(
            credentials,
            mock_donor_credentials,
            mock_authorizedsession_sign,
            expected_url,
        )

    def test_sign_bytes_nonGdu(
        self, mock_donor_credentials, mock_authorizedsession_sign
    ):
        source_credentials = service_account.Credentials(
            SIGNER, "some@email.com", TOKEN_URI, universe_domain="foo.bar"
        )
        credentials = self.make_credentials(
            lifetime=None, source_credentials=source_credentials
        )
        expected_url = "https://iamcredentials.foo.bar/v1/projects/-/serviceAccounts/impersonated@project.iam.gserviceaccount.com:signBlob"
        self._sign_bytes_helper(
            credentials,
            mock_donor_credentials,
            mock_authorizedsession_sign,
            expected_url,
        )

    def _sign_bytes_helper(
        self,
        credentials,
        mock_donor_credentials,
        mock_authorizedsession_sign,
        expected_url,
    ):
        token = "token"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        token_response_body = {"accessToken": token, "expireTime": expire_time}

        response = mock.create_autospec(transport.Response, instance=False)
        response.status = http_client.OK
        response.data = _helpers.to_bytes(json.dumps(token_response_body))

        request = mock.create_autospec(transport.Request, instance=False)
        request.return_value = response

        credentials.refresh(request)
        assert credentials.valid
        assert not credentials.expired

        signature = credentials.sign_bytes(b"signed bytes")
        mock_authorizedsession_sign.assert_called_with(
            mock.ANY,
            "POST",
            expected_url,
            None,
            json={"payload": "c2lnbmVkIGJ5dGVz", "delegates": []},
            headers={"Content-Type": "application/json"},
        )

        assert signature == b"signature"

    def test_sign_bytes_failure(self):
        credentials = self.make_credentials(lifetime=None)

        with mock.patch(
            "google.auth.transport.requests.AuthorizedSession.request", autospec=True
        ) as auth_session:
            data = {"error": {"code": 403, "message": "unauthorized"}}
            mock_response = MockResponse(data, http_client.UNAUTHORIZED)
            auth_session.return_value = mock_response

            with pytest.raises(exceptions.TransportError) as excinfo:
                credentials.sign_bytes(b"foo")
            assert excinfo.match("'code': 403")

    @mock.patch("time.sleep", return_value=None)
    def test_sign_bytes_retryable_failure(self, mock_time):
        credentials = self.make_credentials(lifetime=None)

        with mock.patch(
            "google.auth.transport.requests.AuthorizedSession.request", autospec=True
        ) as auth_session:
            data = {"error": {"code": 500, "message": "internal_failure"}}
            mock_response = MockResponse(data, http_client.INTERNAL_SERVER_ERROR)
            auth_session.return_value = mock_response

            with pytest.raises(exceptions.TransportError) as excinfo:
                credentials.sign_bytes(b"foo")
            assert excinfo.match("exhausted signBlob endpoint retries")

    def test_with_quota_project(self):
        credentials = self.make_credentials()

        quota_project_creds = credentials.with_quota_project("project-foo")
        assert quota_project_creds._quota_project_id == "project-foo"

    @pytest.mark.parametrize("use_data_bytes", [True, False])
    def test_with_quota_project_iam_endpoint_override(
        self, use_data_bytes, mock_donor_credentials
    ):
        credentials = self.make_credentials(
            lifetime=None, iam_endpoint_override=self.IAM_ENDPOINT_OVERRIDE
        )
        token = "token"
        # iam_endpoint_override should be copied to created credentials.
        quota_project_creds = credentials.with_quota_project("project-foo")

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body),
            status=http_client.OK,
            use_data_bytes=use_data_bytes,
        )

        quota_project_creds.refresh(request)

        assert quota_project_creds.valid
        assert not quota_project_creds.expired
        # Confirm override endpoint used.
        request_kwargs = request.call_args[1]
        assert request_kwargs["url"] == self.IAM_ENDPOINT_OVERRIDE

    def test_with_scopes(self):
        credentials = self.make_credentials()
        credentials._target_scopes = []
        assert credentials.requires_scopes is True
        credentials = credentials.with_scopes(["fake_scope1", "fake_scope2"])
        assert credentials.requires_scopes is False
        assert credentials._target_scopes == ["fake_scope1", "fake_scope2"]

    def test_with_scopes_provide_default_scopes(self):
        credentials = self.make_credentials()
        credentials._target_scopes = []
        credentials = credentials.with_scopes(
            ["fake_scope1"], default_scopes=["fake_scope2"]
        )
        assert credentials._target_scopes == ["fake_scope1"]

    def test_id_token_success(
        self, mock_donor_credentials, mock_authorizedsession_idtoken
    ):
        credentials = self.make_credentials(lifetime=None)
        token = "token"
        target_audience = "https://foo.bar"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body), status=http_client.OK
        )

        credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired

        id_creds = impersonated_credentials.IDTokenCredentials(
            credentials, target_audience=target_audience
        )
        id_creds.refresh(request)

        assert id_creds.token == ID_TOKEN_DATA
        assert id_creds.expiry == datetime.datetime.utcfromtimestamp(ID_TOKEN_EXPIRY)

    def test_id_token_metrics(self, mock_donor_credentials):
        credentials = self.make_credentials(lifetime=None)
        credentials.token = "token"
        credentials.expiry = None
        target_audience = "https://foo.bar"

        id_creds = impersonated_credentials.IDTokenCredentials(
            credentials, target_audience=target_audience
        )

        with mock.patch(
            "google.auth.metrics.token_request_id_token_impersonate",
            return_value=ID_TOKEN_REQUEST_METRICS_HEADER_VALUE,
        ):
            with mock.patch(
                "google.auth.transport.requests.AuthorizedSession.post", autospec=True
            ) as mock_post:
                data = {"token": ID_TOKEN_DATA}
                mock_post.return_value = MockResponse(data, http_client.OK)
                id_creds.refresh(None)

                assert id_creds.token == ID_TOKEN_DATA
                assert id_creds.expiry == datetime.datetime.utcfromtimestamp(
                    ID_TOKEN_EXPIRY
                )
                assert (
                    mock_post.call_args.kwargs["headers"]["x-goog-api-client"]
                    == ID_TOKEN_REQUEST_METRICS_HEADER_VALUE
                )

    def test_id_token_from_credential(
        self, mock_donor_credentials, mock_authorizedsession_idtoken
    ):
        credentials = self.make_credentials(lifetime=None)
        target_credentials = self.make_credentials(lifetime=None)
        expected_url = "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/impersonated@project.iam.gserviceaccount.com:generateIdToken"
        self._test_id_token_helper(
            credentials,
            target_credentials,
            mock_donor_credentials,
            mock_authorizedsession_idtoken,
            expected_url,
        )

    def test_id_token_from_credential_nonGdu(
        self, mock_donor_credentials, mock_authorizedsession_idtoken
    ):
        source_credentials = service_account.Credentials(
            SIGNER, "some@email.com", TOKEN_URI, universe_domain="foo.bar"
        )
        credentials = self.make_credentials(
            lifetime=None, source_credentials=source_credentials
        )
        target_credentials = self.make_credentials(
            lifetime=None, source_credentials=source_credentials
        )
        expected_url = "https://iamcredentials.foo.bar/v1/projects/-/serviceAccounts/impersonated@project.iam.gserviceaccount.com:generateIdToken"
        self._test_id_token_helper(
            credentials,
            target_credentials,
            mock_donor_credentials,
            mock_authorizedsession_idtoken,
            expected_url,
        )

    def _test_id_token_helper(
        self,
        credentials,
        target_credentials,
        mock_donor_credentials,
        mock_authorizedsession_idtoken,
        expected_url,
    ):
        token = "token"
        target_audience = "https://foo.bar"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body), status=http_client.OK
        )

        credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired

        id_creds = impersonated_credentials.IDTokenCredentials(
            credentials, target_audience=target_audience, include_email=True
        )
        id_creds = id_creds.from_credentials(target_credentials=target_credentials)
        id_creds.refresh(request)

        args = mock_authorizedsession_idtoken.call_args.args

        assert args[2] == expected_url

        assert id_creds.token == ID_TOKEN_DATA
        assert id_creds._include_email is True
        assert id_creds._target_credentials is target_credentials

    def test_id_token_with_target_audience(
        self, mock_donor_credentials, mock_authorizedsession_idtoken
    ):
        credentials = self.make_credentials(lifetime=None)
        token = "token"
        target_audience = "https://foo.bar"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body), status=http_client.OK
        )

        credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired

        id_creds = impersonated_credentials.IDTokenCredentials(
            credentials, include_email=True
        )
        id_creds = id_creds.with_target_audience(target_audience=target_audience)
        id_creds.refresh(request)

        assert id_creds.token == ID_TOKEN_DATA
        assert id_creds.expiry == datetime.datetime.utcfromtimestamp(ID_TOKEN_EXPIRY)
        assert id_creds._include_email is True

    def test_id_token_invalid_cred(
        self, mock_donor_credentials, mock_authorizedsession_idtoken
    ):
        credentials = None

        with pytest.raises(exceptions.GoogleAuthError) as excinfo:
            impersonated_credentials.IDTokenCredentials(credentials)

        assert excinfo.match("Provided Credential must be" " impersonated_credentials")

    def test_id_token_with_include_email(
        self, mock_donor_credentials, mock_authorizedsession_idtoken
    ):
        credentials = self.make_credentials(lifetime=None)
        token = "token"
        target_audience = "https://foo.bar"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body), status=http_client.OK
        )

        credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired

        id_creds = impersonated_credentials.IDTokenCredentials(
            credentials, target_audience=target_audience
        )
        id_creds = id_creds.with_include_email(True)
        id_creds.refresh(request)

        assert id_creds.token == ID_TOKEN_DATA

    def test_id_token_with_quota_project(
        self, mock_donor_credentials, mock_authorizedsession_idtoken
    ):
        credentials = self.make_credentials(lifetime=None)
        token = "token"
        target_audience = "https://foo.bar"

        expire_time = (
            _helpers.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=500)
        ).isoformat("T") + "Z"
        response_body = {"accessToken": token, "expireTime": expire_time}

        request = self.make_request(
            data=json.dumps(response_body), status=http_client.OK
        )

        credentials.refresh(request)

        assert credentials.valid
        assert not credentials.expired

        id_creds = impersonated_credentials.IDTokenCredentials(
            credentials, target_audience=target_audience
        )
        id_creds = id_creds.with_quota_project("project-foo")
        id_creds.refresh(request)

        assert id_creds.quota_project_id == "project-foo"

    def test_sign_jwt_request_success(self):
        principal = "foo@example.com"
        expected_signed_jwt = "correct_signed_jwt"

        response_body = {"keyId": "1", "signedJwt": expected_signed_jwt}
        request = self.make_request(
            data=json.dumps(response_body), status=http_client.OK
        )

        signed_jwt = impersonated_credentials._sign_jwt_request(
            request=request, principal=principal, headers={}, payload={}
        )

        assert signed_jwt == expected_signed_jwt
        request.assert_called_once_with(
            url="https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/foo@example.com:signJwt",
            method="POST",
            headers={},
            body=json.dumps({"delegates": [], "payload": json.dumps({})}).encode(
                "utf-8"
            ),
        )

    def test_sign_jwt_request_http_error(self):
        principal = "foo@example.com"

        request = self.make_request(
            data="error_message", status=http_client.BAD_REQUEST
        )

        with pytest.raises(exceptions.RefreshError) as excinfo:
            _ = impersonated_credentials._sign_jwt_request(
                request=request, principal=principal, headers={}, payload={}
            )

        assert excinfo.match(impersonated_credentials._REFRESH_ERROR)

        assert excinfo.value.args[0] == "Unable to acquire impersonated credentials"
        assert excinfo.value.args[1] == "error_message"

    def test_sign_jwt_request_invalid_response_error(self):
        principal = "foo@example.com"

        request = self.make_request(data="invalid_data", status=http_client.OK)

        with pytest.raises(exceptions.RefreshError) as excinfo:
            _ = impersonated_credentials._sign_jwt_request(
                request=request, principal=principal, headers={}, payload={}
            )

        assert excinfo.match(impersonated_credentials._REFRESH_ERROR)

        assert (
            excinfo.value.args[0]
            == "Unable to acquire impersonated credentials: No signed JWT in response."
        )
        assert excinfo.value.args[1] == "invalid_data"
