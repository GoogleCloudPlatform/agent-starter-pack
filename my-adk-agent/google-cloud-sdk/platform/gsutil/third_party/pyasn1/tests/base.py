#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import unittest

from pyasn1 import debug


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        debug.setLogger(debug.Debug('all', printer=lambda *x: None))

    def tearDown(self):
        debug.setLogger(None)
