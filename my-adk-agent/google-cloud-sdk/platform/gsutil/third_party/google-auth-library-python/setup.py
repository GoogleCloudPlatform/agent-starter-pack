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

import io
import os

from setuptools import find_namespace_packages
from setuptools import setup


DEPENDENCIES = (
    "cachetools>=2.0.0,<6.0",
    "pyasn1-modules>=0.2.1",
    # rsa==4.5 is the last version to support 2.7
    # https://github.com/sybrenstuvel/python-rsa/issues/152#issuecomment-643470233
    "rsa>=3.1.4,<5",
)

# TODO(https://github.com/googleapis/google-auth-library-python/issues/1737): Unit test fails with
#  `No module named 'cryptography.hazmat.backends.openssl.x509' for Python 3.7``.
cryptography_base_require = [
    "cryptography >= 38.0.3",
    "cryptography < 39.0.0; python_version < '3.8'",
]

requests_extra_require = ["requests >= 2.20.0, < 3.0.0"]

aiohttp_extra_require = ["aiohttp >= 3.6.2, < 4.0.0", *requests_extra_require]

pyjwt_extra_require = ["pyjwt>=2.0", *cryptography_base_require]

reauth_extra_require = ["pyu2f>=0.1.5"]

# TODO(https://github.com/googleapis/google-auth-library-python/issues/1738): Add bounds for cryptography and pyopenssl dependencies.
enterprise_cert_extra_require = ["cryptography", "pyopenssl"]

pyopenssl_extra_require = ["pyopenssl>=20.0.0", cryptography_base_require]

# TODO(https://github.com/googleapis/google-auth-library-python/issues/1739): Add bounds for urllib3 and packaging dependencies.
urllib3_extra_require = ["urllib3", "packaging"]

# Unit test requirements.
testing_extra_require = [
    # TODO(https://github.com/googleapis/google-auth-library-python/issues/1735): Remove `grpcio` from testing requirements once an extra is added for `grpcio` dependency.
    "grpcio",
    "flask",
    "freezegun",
    "mock",
    # TODO(https://github.com/googleapis/google-auth-library-python/issues/1736): Remove `oauth2client` from testing requirements once an extra is added for `oauth2client` dependency.
    "oauth2client",
    *pyjwt_extra_require,
    "pytest",
    "pytest-cov",
    "pytest-localserver",
    *pyopenssl_extra_require,
    *reauth_extra_require,
    "responses",
    *urllib3_extra_require,
    # Async Dependencies
    *aiohttp_extra_require,
    "aioresponses",
    "pytest-asyncio",
    # TODO(https://github.com/googleapis/google-auth-library-python/issues/1665): Remove the pinned version of pyopenssl
    # once `TestDecryptPrivateKey::test_success` is updated to remove the deprecated `OpenSSL.crypto.sign` and
    # `OpenSSL.crypto.verify` methods. See: https://www.pyopenssl.org/en/latest/changelog.html#id3.
    "pyopenssl < 24.3.0",
    # TODO(https://github.com/googleapis/google-auth-library-python/issues/1722): `test_aiohttp_requests` depend on
    # aiohttp < 3.10.0 which is a bug. Investigate and remove the pinned aiohttp version.
    "aiohttp < 3.10.0",
]

extras = {
    "aiohttp": aiohttp_extra_require,
    "enterprise_cert": enterprise_cert_extra_require,
    "pyopenssl": pyopenssl_extra_require,
    "pyjwt": pyjwt_extra_require,
    "reauth": reauth_extra_require,
    "requests": requests_extra_require,
    "testing": testing_extra_require,
    "urllib3": urllib3_extra_require,
    # TODO(https://github.com/googleapis/google-auth-library-python/issues/1735): Add an extra for `grpcio` dependency.
    # TODO(https://github.com/googleapis/google-auth-library-python/issues/1736): Add an extra for `oauth2client` dependency.
}

with io.open("README.rst", "r") as fh:
    long_description = fh.read()

package_root = os.path.abspath(os.path.dirname(__file__))

version = {}
with open(os.path.join(package_root, "google/auth/version.py")) as fp:
    exec(fp.read(), version)
version = version["__version__"]

setup(
    name="google-auth",
    version=version,
    author="Google Cloud Platform",
    author_email="googleapis-packages@google.com",
    description="Google Authentication Library",
    long_description=long_description,
    url="https://github.com/googleapis/google-auth-library-python",
    packages=find_namespace_packages(
        exclude=("tests*", "system_tests*", "docs*", "samples*")
    ),
    package_data={"google.auth": ["py.typed"], "google.oauth2": ["py.typed"]},
    install_requires=DEPENDENCIES,
    extras_require=extras,
    python_requires=">=3.7",
    license="Apache 2.0",
    keywords="google auth oauth client",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
