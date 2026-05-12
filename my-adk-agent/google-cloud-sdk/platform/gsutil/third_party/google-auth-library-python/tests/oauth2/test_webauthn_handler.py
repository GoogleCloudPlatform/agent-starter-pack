import json
import struct

import mock
import pytest  # type: ignore

from google.auth import exceptions
from google.oauth2 import webauthn_handler
from google.oauth2 import webauthn_types


@pytest.fixture
def os_get_stub():
    with mock.patch.object(
        webauthn_handler.os.environ,
        "get",
        return_value="gcloud_webauthn_plugin",
        name="fake os.environ.get",
    ) as mock_os_environ_get:
        yield mock_os_environ_get


@pytest.fixture
def subprocess_run_stub():
    with mock.patch.object(
        webauthn_handler.subprocess, "run", name="fake subprocess.run"
    ) as mock_subprocess_run:
        yield mock_subprocess_run


def test_PluginHandler_is_available(os_get_stub):
    test_handler = webauthn_handler.PluginHandler()

    assert test_handler.is_available() is True

    os_get_stub.return_value = None
    assert test_handler.is_available() is False


GET_ASSERTION_REQUEST = webauthn_types.GetRequest(
    origin="fake_origin",
    rpid="fake_rpid",
    challenge="fake_challenge",
    allow_credentials=[webauthn_types.PublicKeyCredentialDescriptor(id="fake_id_1")],
)


def test_malformated_get_assertion_response(os_get_stub, subprocess_run_stub):
    response_len = struct.pack("<I", 5)
    response = "1234567890"
    mock_response = mock.Mock()
    mock_response.stdout = response_len + response.encode()
    subprocess_run_stub.return_value = mock_response

    test_handler = webauthn_handler.PluginHandler()
    with pytest.raises(exceptions.MalformedError) as excinfo:
        test_handler.get(GET_ASSERTION_REQUEST)
    assert "Plugin response length" in str(excinfo.value)


def test_failure_get_assertion(os_get_stub, subprocess_run_stub):
    failure_response = {
        "type": "getResponse",
        "error": "fake_plugin_get_assertion_failure",
    }
    response_json = json.dumps(failure_response).encode()
    response_len = struct.pack("<I", len(response_json))

    # process returns get response in json
    mock_response = mock.Mock()
    mock_response.stdout = response_len + response_json
    subprocess_run_stub.return_value = mock_response

    test_handler = webauthn_handler.PluginHandler()
    with pytest.raises(exceptions.ReauthFailError) as excinfo:
        test_handler.get(GET_ASSERTION_REQUEST)
    assert failure_response["error"] in str(excinfo.value)


def test_success_get_assertion(os_get_stub, subprocess_run_stub):
    success_response = {
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
    valid_plugin_response = {"type": "getResponse", "responseData": success_response}
    valid_plugin_response_json = json.dumps(valid_plugin_response).encode()
    valid_plugin_response_len = struct.pack("<I", len(valid_plugin_response_json))

    # process returns get response in json
    mock_response = mock.Mock()
    mock_response.stdout = valid_plugin_response_len + valid_plugin_response_json
    subprocess_run_stub.return_value = mock_response

    # Call get()
    test_handler = webauthn_handler.PluginHandler()
    got_response = test_handler.get(GET_ASSERTION_REQUEST)

    # Validate expected plugin request
    os_get_stub.assert_called_once()
    subprocess_run_stub.assert_called_once()

    stdin_input = subprocess_run_stub.call_args.kwargs["input"]
    input_json_len_le = stdin_input[:4]
    input_json_len = struct.unpack("<I", input_json_len_le)[0]
    input_json = stdin_input[4:]
    assert len(input_json) == input_json_len

    input_dict = json.loads(input_json.decode("utf8"))
    assert input_dict == {
        "type": "get",
        "origin": "fake_origin",
        "requestData": {
            "rpid": "fake_rpid",
            "challenge": "fake_challenge",
            "allowCredentials": [{"type": "public-key", "id": "fake_id_1"}],
        },
    }

    # Validate get assertion response
    assert got_response.id == success_response["id"]
    assert (
        got_response.authenticator_attachment
        == success_response["authenticatorAttachment"]
    )
    assert (
        got_response.client_extension_results
        == success_response["clientExtensionResults"]
    )
    assert (
        got_response.response.client_data_json
        == success_response["response"]["clientDataJSON"]
    )
    assert (
        got_response.response.authenticator_data
        == success_response["response"]["authenticatorData"]
    )
    assert got_response.response.signature == success_response["response"]["signature"]
    assert (
        got_response.response.user_handle == success_response["response"]["userHandle"]
    )
