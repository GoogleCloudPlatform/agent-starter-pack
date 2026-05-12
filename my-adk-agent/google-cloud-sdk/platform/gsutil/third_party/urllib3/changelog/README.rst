This directory contains changelog entries: short files that contain a small
**ReST**-formatted text that will be added to ``CHANGES.rst`` by `towncrier
<https://towncrier.readthedocs.io/en/latest/>`__.

The ``CHANGES.rst`` will be read by **users**, so this description should be aimed to
urllib3 users instead of describing internal changes which are only relevant to the
developers.

Make sure to use full sentences in the **past tense** and use punctuation, examples::

    Added support for HTTPS proxies contacting HTTPS servers.

    Upgraded ``urllib3.utils.parse_url()`` to be RFC 3986 compliant.

Each file should be named like ``<ISSUE>.<TYPE>.rst``, where ``<ISSUE>`` is an issue
number, and ``<TYPE>`` is one of the `five towncrier default types
<https://towncrier.readthedocs.io/en/latest/#news-fragments>`_

So for example: ``123.feature.rst``, ``456.bugfix.rst``.

If your pull request fixes an issue, use that number here. If there is no issue, then
after you submit the pull request and get the pull request number you can add a
changelog using that instead.

If your change does not deserve a changelog entry, apply the `Skip Changelog` GitHub
label to your pull request.

You can also run ``nox -s docs`` to build the documentation with the draft changelog
(``docs/_build/html/changelog.html``) if you want to get a preview of how your change
will look in the final release notes. You can also see a preview from the Read the Docs
check in pull requests.
