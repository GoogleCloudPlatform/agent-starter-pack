#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import unittest

suite = unittest.TestLoader().loadTestsFromNames(
    ['tests.codec.test_streaming.suite',
     'tests.codec.ber.__main__.suite',
     'tests.codec.cer.__main__.suite',
     'tests.codec.der.__main__.suite',
     'tests.codec.native.__main__.suite']
)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
