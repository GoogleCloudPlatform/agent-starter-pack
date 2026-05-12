#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import unittest

suite = unittest.TestLoader().loadTestsFromNames(
    ['tests.type.test_constraint.suite',
     'tests.type.test_opentype.suite',
     'tests.type.test_namedtype.suite',
     'tests.type.test_namedval.suite',
     'tests.type.test_tag.suite',
     'tests.type.test_univ.suite',
     'tests.type.test_char.suite',
     'tests.type.test_useful.suite']
)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
