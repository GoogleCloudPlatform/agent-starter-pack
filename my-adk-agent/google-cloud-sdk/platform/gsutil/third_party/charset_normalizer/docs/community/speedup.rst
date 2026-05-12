Optional speedup extension
==========================

Why?
----

charset-normalizer will always remain pure Python, meaning that a environment without any build capabilities will
run this program without any additional requirements.

Nonetheless, starting from the version 3.0 we introduce and publish some platform specific wheels including a
pre-built extension.

Most of the time is spent in the module `md.py` so we decided to "compile it" using Mypyc.

(1) It does not require to have a separate code base
(2) Our project code base is rather simple and lightweight
(3) Mypyc is robust enough today
(4) Four times faster!

How?
----

If your platform and/or architecture is not served by this swift optimization you may compile it easily yourself.
Following those instructions (provided you have the necessary toolchain installed):

  ::

    export CHARSET_NORMALIZER_USE_MYPYC=1
    pip install mypy build wheel
    pip install charset-normalizer --no-binary :all:


How not to?
-----------

You may install charset-normalizer without the speedups by directly using the universal wheel
(most likely hosted on PyPI or any valid mirror you use) with ``--no-binary``.

E.g. when installing ``requests`` and you don't want to use the ``charset-normalizer`` speedups, you can do:

  ::

    pip install requests --no-binary charset-normalizer


When installing `charset-normalizer` by itself, you can also pass ``:all:`` as the specifier to ``--no-binary``.

  ::

    pip install charset-normalizer --no-binary :all:
