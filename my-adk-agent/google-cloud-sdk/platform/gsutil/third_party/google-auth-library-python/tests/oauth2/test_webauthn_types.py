import json

import pytest  # type: ignore

from google.oauth2 import webauthn_types


@pytest.mark.parametrize(
    "test_pub_key_cred,expected_dict",
    [
        (
            webauthn_types.PublicKeyCredentialDescriptor(
                id="fake_cred_id_base64", transports=None
            ),
            {"type": "public-key", "id": "fake_cred_id_base64"},
        ),
        (
            webauthn_types.PublicKeyCredentialDescriptor(
                id="fake_cred_id_base64", transports=[]
            ),
            {"type": "public-key", "id": "fake_cred_id_base64"},
        ),
        (
            webauthn_types.PublicKeyCredentialDescriptor(
                id="fake_cred_id_base64", transports=["usb"]
            ),
            {"type": "public-key", "id": "fake_cred_id_base64", "transports": ["usb"]},
        ),
        (
            webauthn_types.PublicKeyCredentialDescriptor(
                id="fake_cred_id_base64", transports=["usb", "internal"]
            ),
            {
                "type": "public-key",
                "id": "fake_cred_id_base64",
                "transports": ["usb", "internal"],
            },
        ),
    ],
)
def test_PublicKeyCredentialDescriptor(test_pub_key_cred, expected_dict):
    assert test_pub_key_cred.to_dict() == expected_dict


@pytest.mark.parametrize(
    "test_extension_input,expected_dict",
    [
        (webauthn_types.AuthenticationExtensionsClientInputs(), {}),
        (webauthn_types.AuthenticationExtensionsClientInputs(appid=""), {}),
        (
            webauthn_types.AuthenticationExtensionsClientInputs(appid="fake_appid"),
            {"appid": "fake_appid"},
        ),
    ],
)
def test_AuthenticationExtensionsClientInputs(test_extension_input, expected_dict):
    assert test_extension_input.to_dict() == expected_dict


@pytest.mark.parametrize("has_allow_credentials", [(False), (True)])
def test_GetRequest(has_allow_credentials):
    allow_credentials = [
        webauthn_types.PublicKeyCredentialDescriptor(id="fake_id_1"),
        webauthn_types.PublicKeyCredentialDescriptor(id="fake_id_2"),
    ]
    test_get_request = webauthn_types.GetRequest(
        origin="fake_origin",
        rpid="fake_rpid",
        challenge="fake_challenge",
        timeout_ms=123,
        allow_credentials=allow_credentials if has_allow_credentials else None,
        user_verification="preferred",
        extensions=webauthn_types.AuthenticationExtensionsClientInputs(
            appid="fake_appid"
        ),
    )
    expected_allow_credentials = [
        {"type": "public-key", "id": "fake_id_1"},
        {"type": "public-key", "id": "fake_id_2"},
    ]
    exepcted_dict = {
        "type": "get",
        "origin": "fake_origin",
        "requestData": {
            "rpid": "fake_rpid",
            "timeout": 123,
            "challenge": "fake_challenge",
            "userVerification": "preferred",
            "extensions": {"appid": "fake_appid"},
        },
    }
    if has_allow_credentials:
        exepcted_dict["requestData"]["allowCredentials"] = expected_allow_credentials
    assert json.loads(test_get_request.to_json()) == exepcted_dict


@pytest.mark.parametrize(
    "has_user_handle,has_authenticator_attachment,has_client_extension_results",
    [
        (False, False, False),
        (False, False, True),
        (False, True, False),
        (False, True, True),
        (True, False, False),
        (True, False, True),
        (True, True, False),
        (True, True, True),
    ],
)
def test_GetResponse(
    has_user_handle, has_authenticator_attachment, has_client_extension_results
):
    input_response_data = {
        "type": "public-key",
        "id": "fake-id",
        "authenticatorAttachment": "cross-platform",
        "clientExtensionResults": {"appid": True},
        "response": {
            "clientDataJSON": "fake_client_data_json_base64",
            "authenticatorData": "fake_authenticator_data_base64",
            "signature": "fake_signature_base64",
            "userHandle": "fake_user_handle_base64",
        },
    }
    if not has_authenticator_attachment:
        input_response_data.pop("authenticatorAttachment")
    if not has_client_extension_results:
        input_response_data.pop("clientExtensionResults")
    if not has_user_handle:
        input_response_data["response"].pop("userHandle")

    response = webauthn_types.GetResponse.from_json(
        json.dumps({"type": "getResponse", "responseData": input_response_data})
    )

    assert response.id == input_response_data["id"]
    assert response.authenticator_attachment == (
        input_response_data["authenticatorAttachment"]
        if has_authenticator_attachment
        else None
    )
    assert response.client_extension_results == (
        input_response_data["clientExtensionResults"]
        if has_client_extension_results
        else None
    )
    assert (
        response.response.client_data_json
        == input_response_data["response"]["clientDataJSON"]
    )
    assert (
        response.response.authenticator_data
        == input_response_data["response"]["authenticatorData"]
    )
    assert response.response.signature == input_response_data["response"]["signature"]
    assert response.response.user_handle == (
        input_response_data["response"]["userHandle"] if has_user_handle else None
    )


@pytest.mark.parametrize(
    "input_dict,expected_error",
    [
        ({"xyz_type": "wrong_type"}, "Invalid Get response type"),
        ({"type": "wrong_type"}, "Invalid Get response type"),
        ({"type": "getResponse"}, "Get response is empty"),
        (
            {"type": "getResponse", "error": "fake_get_response_error"},
            "WebAuthn.get failure: fake_get_response_error",
        ),
        (
            {"type": "getResponse", "responseData": {"xyz_type": "wrong_type"}},
            "Invalid credential type",
        ),
        (
            {"type": "getResponse", "responseData": {"type": "wrong_type"}},
            "Invalid credential type",
        ),
        (
            {
                "type": "getResponse",
                "responseData": {"type": "public-key", "response": {}},
            },
            "KeyError",
        ),
        (
            {
                "type": "getResponse",
                "responseData": {
                    "type": "public-key",
                    "response": {"clientDataJSON": "fake_client_data_json_base64"},
                },
            },
            "KeyError",
        ),
        (
            {
                "type": "getResponse",
                "responseData": {
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "fake_client_data_json_base64",
                        "authenticatorData": "fake_authenticator_data_base64",
                    },
                },
            },
            "KeyError",
        ),
        (
            {
                "type": "getResponse",
                "responseData": {
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "fake_client_data_json_base64",
                        "authenticatorData": "fake_authenticator_data_base64",
                        "signature": "fake_signature_base64",
                    },
                },
            },
            "KeyError",
        ),
    ],
)
def test_GetResponse_error(input_dict, expected_error):
    with pytest.raises(Exception) as excinfo:
        webauthn_types.GetResponse.from_json(json.dumps(input_dict))
    if expected_error == "KeyError":
        assert excinfo.type is KeyError
    else:
        assert expected_error in str(excinfo.value)


def test_MalformatedJsonInput():
    with pytest.raises(ValueError) as excinfo:
        webauthn_types.GetResponse.from_json(")]}")
    assert "Invalid Get JSON response" in str(excinfo.value)
