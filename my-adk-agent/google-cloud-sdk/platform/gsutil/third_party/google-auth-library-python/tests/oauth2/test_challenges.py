# Copyright 2021 Google LLC
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

"""Tests for the reauth module."""

import base64
import os
import sys

import mock
import pytest  # type: ignore
import pyu2f  # type: ignore

from google.auth import exceptions
from google.oauth2 import challenges
from google.oauth2.webauthn_types import (
    AuthenticationExtensionsClientInputs,
    AuthenticatorAssertionResponse,
    GetRequest,
    GetResponse,
    PublicKeyCredentialDescriptor,
)


def test_get_user_password():
    with mock.patch("getpass.getpass", return_value="foo"):
        assert challenges.get_user_password("") == "foo"


def test_security_key():
    metadata = {
        "status": "READY",
        "challengeId": 2,
        "challengeType": "SECURITY_KEY",
        "securityKey": {
            "applicationId": "security_key_application_id",
            "challenges": [
                {
                    "keyHandle": "some_key",
                    "challenge": base64.urlsafe_b64encode(
                        "some_challenge".encode("ascii")
                    ).decode("ascii"),
                }
            ],
            "relyingPartyId": "security_key_application_id",
        },
    }
    mock_key = mock.Mock()

    challenge = challenges.SecurityKeyChallenge()

    # Test the case that security key challenge is passed with applicationId and
    # relyingPartyId the same.
    os.environ.pop('"GOOGLE_AUTH_WEBAUTHN_PLUGIN"', None)

    with mock.patch("pyu2f.model.RegisteredKey", return_value=mock_key):
        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            mock_authenticate.return_value = "security key response"
            assert challenge.name == "SECURITY_KEY"
            assert challenge.is_locally_eligible
            assert challenge.obtain_challenge_input(metadata) == {
                "securityKey": "security key response"
            }
            mock_authenticate.assert_called_with(
                "security_key_application_id",
                [{"key": mock_key, "challenge": b"some_challenge"}],
                print_callback=sys.stderr.write,
            )

    # Test the case that webauthn plugin is available
    os.environ["GOOGLE_AUTH_WEBAUTHN_PLUGIN"] = "plugin"

    with mock.patch(
        "google.oauth2.challenges.SecurityKeyChallenge._obtain_challenge_input_webauthn",
        return_value={"securityKey": "security key response"},
    ):

        assert challenge.obtain_challenge_input(metadata) == {
            "securityKey": "security key response"
        }
    os.environ.pop('"GOOGLE_AUTH_WEBAUTHN_PLUGIN"', None)

    # Test the case that security key challenge is passed with applicationId and
    # relyingPartyId different, first call works.
    metadata["securityKey"]["relyingPartyId"] = "security_key_relying_party_id"
    sys.stderr.write("metadata=" + str(metadata) + "\n")
    with mock.patch("pyu2f.model.RegisteredKey", return_value=mock_key):
        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            mock_authenticate.return_value = "security key response"
            assert challenge.name == "SECURITY_KEY"
            assert challenge.is_locally_eligible
            assert challenge.obtain_challenge_input(metadata) == {
                "securityKey": "security key response"
            }
            mock_authenticate.assert_called_with(
                "security_key_relying_party_id",
                [{"key": mock_key, "challenge": b"some_challenge"}],
                print_callback=sys.stderr.write,
            )

    # Test the case that security key challenge is passed with applicationId and
    # relyingPartyId different, first call fails, requires retry.
    metadata["securityKey"]["relyingPartyId"] = "security_key_relying_party_id"
    with mock.patch("pyu2f.model.RegisteredKey", return_value=mock_key):
        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            assert challenge.name == "SECURITY_KEY"
            assert challenge.is_locally_eligible
            mock_authenticate.side_effect = [
                pyu2f.errors.U2FError(pyu2f.errors.U2FError.DEVICE_INELIGIBLE),
                "security key response",
            ]
            assert challenge.obtain_challenge_input(metadata) == {
                "securityKey": "security key response"
            }
            calls = [
                mock.call(
                    "security_key_relying_party_id",
                    [{"key": mock_key, "challenge": b"some_challenge"}],
                    print_callback=sys.stderr.write,
                ),
                mock.call(
                    "security_key_application_id",
                    [{"key": mock_key, "challenge": b"some_challenge"}],
                    print_callback=sys.stderr.write,
                ),
            ]
            mock_authenticate.assert_has_calls(calls)

    # Test various types of exceptions.
    with mock.patch("pyu2f.model.RegisteredKey", return_value=mock_key):
        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            mock_authenticate.side_effect = pyu2f.errors.U2FError(
                pyu2f.errors.U2FError.DEVICE_INELIGIBLE
            )
            assert challenge.obtain_challenge_input(metadata) is None

        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            mock_authenticate.side_effect = pyu2f.errors.U2FError(
                pyu2f.errors.U2FError.TIMEOUT
            )
            assert challenge.obtain_challenge_input(metadata) is None

        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            mock_authenticate.side_effect = pyu2f.errors.PluginError()
            assert challenge.obtain_challenge_input(metadata) is None

        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            mock_authenticate.side_effect = pyu2f.errors.U2FError(
                pyu2f.errors.U2FError.BAD_REQUEST
            )
            with pytest.raises(pyu2f.errors.U2FError):
                challenge.obtain_challenge_input(metadata)

        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            mock_authenticate.side_effect = pyu2f.errors.NoDeviceFoundError()
            assert challenge.obtain_challenge_input(metadata) is None

        with mock.patch(
            "pyu2f.convenience.authenticator.CompositeAuthenticator.Authenticate"
        ) as mock_authenticate:
            mock_authenticate.side_effect = pyu2f.errors.UnsupportedVersionException()
            with pytest.raises(pyu2f.errors.UnsupportedVersionException):
                challenge.obtain_challenge_input(metadata)

        with mock.patch.dict("sys.modules"):
            sys.modules["pyu2f"] = None
            with pytest.raises(exceptions.ReauthFailError) as excinfo:
                challenge.obtain_challenge_input(metadata)
            assert excinfo.match(r"pyu2f dependency is required")


def test_security_key_webauthn():
    metadata = {
        "status": "READY",
        "challengeId": 2,
        "challengeType": "SECURITY_KEY",
        "securityKey": {
            "applicationId": "security_key_application_id",
            "challenges": [
                {
                    "keyHandle": "some_key",
                    "challenge": base64.urlsafe_b64encode(
                        "some_challenge".encode("ascii")
                    ).decode("ascii"),
                }
            ],
            "relyingPartyId": "security_key_application_id",
        },
    }

    challenge = challenges.SecurityKeyChallenge()

    sk = metadata["securityKey"]
    sk_challenges = sk["challenges"]

    application_id = sk["applicationId"]

    allow_credentials = []
    for sk_challenge in sk_challenges:
        allow_credentials.append(
            PublicKeyCredentialDescriptor(id=sk_challenge["keyHandle"])
        )

    extension = AuthenticationExtensionsClientInputs(appid=application_id)

    get_request = GetRequest(
        origin=challenges.REAUTH_ORIGIN,
        rpid=application_id,
        challenge=challenge._unpadded_urlsafe_b64recode(sk_challenge["challenge"]),
        timeout_ms=challenges.WEBAUTHN_TIMEOUT_MS,
        allow_credentials=allow_credentials,
        user_verification="required",
        extensions=extension,
    )

    assertion_resp = AuthenticatorAssertionResponse(
        client_data_json="clientDataJSON",
        authenticator_data="authenticatorData",
        signature="signature",
        user_handle="userHandle",
    )
    get_response = GetResponse(
        id="id",
        response=assertion_resp,
        authenticator_attachment="authenticatorAttachment",
        client_extension_results="clientExtensionResults",
    )
    response = {
        "clientData": get_response.response.client_data_json,
        "authenticatorData": get_response.response.authenticator_data,
        "signatureData": get_response.response.signature,
        "applicationId": "security_key_application_id",
        "keyHandle": get_response.id,
        "securityKeyReplyType": 2,
    }

    mock_handler = mock.Mock()
    mock_handler.get.return_value = get_response

    # Test success case
    assert challenge._obtain_challenge_input_webauthn(metadata, mock_handler) == {
        "securityKey": response
    }
    mock_handler.get.assert_called_with(get_request)

    # Test exceptions

    # Missing Values
    sk = metadata["securityKey"]
    metadata["securityKey"] = None
    with pytest.raises(exceptions.InvalidValue):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)
    metadata["securityKey"] = sk

    c = metadata["securityKey"]["challenges"]
    metadata["securityKey"]["challenges"] = None
    with pytest.raises(exceptions.InvalidValue):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)
    metadata["securityKey"]["challenges"] = []
    with pytest.raises(exceptions.InvalidValue):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)
    metadata["securityKey"]["challenges"] = c

    aid = metadata["securityKey"]["applicationId"]
    metadata["securityKey"]["applicationId"] = None
    with pytest.raises(exceptions.InvalidValue):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)
    metadata["securityKey"]["applicationId"] = aid

    rpi = metadata["securityKey"]["relyingPartyId"]
    metadata["securityKey"]["relyingPartyId"] = None
    with pytest.raises(exceptions.InvalidValue):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)
    metadata["securityKey"]["relyingPartyId"] = rpi

    kh = metadata["securityKey"]["challenges"][0]["keyHandle"]
    metadata["securityKey"]["challenges"][0]["keyHandle"] = None
    with pytest.raises(exceptions.InvalidValue):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)
    metadata["securityKey"]["challenges"][0]["keyHandle"] = kh

    ch = metadata["securityKey"]["challenges"][0]["challenge"]
    metadata["securityKey"]["challenges"][0]["challenge"] = None
    with pytest.raises(exceptions.InvalidValue):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)
    metadata["securityKey"]["challenges"][0]["challenge"] = ch

    # Handler Exceptions
    mock_handler.get.side_effect = exceptions.MalformedError
    with pytest.raises(exceptions.MalformedError):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)

    mock_handler.get.side_effect = exceptions.InvalidResource
    with pytest.raises(exceptions.InvalidResource):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)

    mock_handler.get.side_effect = exceptions.ReauthFailError
    with pytest.raises(exceptions.ReauthFailError):
        challenge._obtain_challenge_input_webauthn(metadata, mock_handler)


@mock.patch("getpass.getpass", return_value="foo")
def test_password_challenge(getpass_mock):
    challenge = challenges.PasswordChallenge()

    with mock.patch("getpass.getpass", return_value="foo"):
        assert challenge.is_locally_eligible
        assert challenge.name == "PASSWORD"
        assert challenges.PasswordChallenge().obtain_challenge_input({}) == {
            "credential": "foo"
        }

    with mock.patch("getpass.getpass", return_value=None):
        assert challenges.PasswordChallenge().obtain_challenge_input({}) == {
            "credential": " "
        }


def test_saml_challenge():
    challenge = challenges.SamlChallenge()
    assert challenge.is_locally_eligible
    assert challenge.name == "SAML"
    with pytest.raises(exceptions.ReauthSamlChallengeFailError):
        challenge.obtain_challenge_input(None)
