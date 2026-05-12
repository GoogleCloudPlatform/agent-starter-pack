import mock
import pytest  # type: ignore

from google.oauth2 import webauthn_handler
from google.oauth2 import webauthn_handler_factory


@pytest.fixture
def os_get_stub():
    with mock.patch.object(
        webauthn_handler.os.environ,
        "get",
        return_value="gcloud_webauthn_plugin",
        name="fake os.environ.get",
    ) as mock_os_environ_get:
        yield mock_os_environ_get


# Check that get_handler returns a value when env is set,
# that type is PluginHandler, and that no value is returned
# if env not set.
def test_WebauthHandlerFactory_get(os_get_stub):
    factory = webauthn_handler_factory.WebauthnHandlerFactory()
    assert factory.get_handler() is not None

    assert isinstance(factory.get_handler(), webauthn_handler.PluginHandler)

    os_get_stub.return_value = None
    assert factory.get_handler() is None
