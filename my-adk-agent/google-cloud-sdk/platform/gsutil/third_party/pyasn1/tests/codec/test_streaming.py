#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2019, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import io
import sys
import unittest

from tests.base import BaseTestCase

from pyasn1.codec import streaming


class CachingStreamWrapperTestCase(BaseTestCase):
    def setUp(self):
        self.shortText = b"abcdefghij"
        self.longText = self.shortText * (io.DEFAULT_BUFFER_SIZE * 5)
        self.shortStream = io.BytesIO(self.shortText)
        self.longStream = io.BytesIO(self.longText)

    def testReadJustFromCache(self):
        wrapper = streaming.CachingStreamWrapper(self.shortStream)
        wrapper.read(6)
        wrapper.seek(3)
        assert wrapper.read(1) == b"d"
        assert wrapper.read(1) == b"e"
        assert wrapper.tell() == 5

    def testReadFromCacheAndStream(self):
        wrapper = streaming.CachingStreamWrapper(self.shortStream)
        wrapper.read(6)
        wrapper.seek(3)
        assert wrapper.read(4) == b"defg"
        assert wrapper.tell() == 7

    def testReadJustFromStream(self):
        wrapper = streaming.CachingStreamWrapper(self.shortStream)
        assert wrapper.read(6) == b"abcdef"
        assert wrapper.tell() == 6

    def testPeek(self):
        wrapper = streaming.CachingStreamWrapper(self.longStream)
        read_bytes = wrapper.peek(io.DEFAULT_BUFFER_SIZE + 73)
        assert len(read_bytes) == io.DEFAULT_BUFFER_SIZE + 73
        assert read_bytes.startswith(b"abcdefg")
        assert wrapper.tell() == 0
        assert wrapper.read(4) == b"abcd"

    def testMarkedPositionResets(self):
        wrapper = streaming.CachingStreamWrapper(self.longStream)
        wrapper.read(10)
        wrapper.markedPosition = wrapper.tell()
        assert wrapper.markedPosition == 10

        # Reach the maximum capacity of cache
        wrapper.read(io.DEFAULT_BUFFER_SIZE)
        assert wrapper.tell() == 10 + io.DEFAULT_BUFFER_SIZE

        # The following should clear the cache
        wrapper.markedPosition = wrapper.tell()
        assert wrapper.markedPosition == 0
        assert len(wrapper._cache.getvalue()) == 0


suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
