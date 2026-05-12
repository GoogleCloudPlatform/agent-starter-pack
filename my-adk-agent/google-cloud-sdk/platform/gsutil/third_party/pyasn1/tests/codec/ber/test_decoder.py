#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import gzip
import io
import os
import sys
import tempfile
import unittest
import zipfile

from tests.base import BaseTestCase

from pyasn1.type import tag
from pyasn1.type import namedtype
from pyasn1.type import opentype
from pyasn1.type import univ
from pyasn1.type import char
from pyasn1.codec import streaming
from pyasn1.codec.ber import decoder
from pyasn1.codec.ber import eoo
from pyasn1 import error


class LargeTagDecoderTestCase(BaseTestCase):
    def testLargeTag(self):
        assert decoder.decode(bytes((127, 141, 245, 182, 253, 47, 3, 2, 1, 1))) == (1, b'')

    def testLongTag(self):
        assert decoder.decode(bytes((0x1f, 2, 1, 0)))[0].tagSet == univ.Integer.tagSet

    def testTagsEquivalence(self):
        integer = univ.Integer(2).subtype(implicitTag=tag.Tag(tag.tagClassContext, 0, 0))
        assert decoder.decode(bytes((0x9f, 0x80, 0x00, 0x02, 0x01, 0x02)), asn1Spec=integer) == decoder.decode(
            bytes((0x9f, 0x00, 0x02, 0x01, 0x02)), asn1Spec=integer)


class DecoderCacheTestCase(BaseTestCase):
    def testCache(self):
        assert decoder.decode(bytes((0x1f, 2, 1, 0))) == decoder.decode(bytes((0x1f, 2, 1, 0)))


class IntegerDecoderTestCase(BaseTestCase):
    def testPosInt(self):
        assert decoder.decode(bytes((2, 1, 12))) == (12, b'')

    def testNegInt(self):
        assert decoder.decode(bytes((2, 1, 244))) == (-12, b'')

    def testZero(self):
        assert decoder.decode(bytes((2, 0))) == (0, b'')

    def testZeroLong(self):
        assert decoder.decode(bytes((2, 1, 0))) == (0, b'')

    def testMinusOne(self):
        assert decoder.decode(bytes((2, 1, 255))) == (-1, b'')

    def testPosLong(self):
        assert decoder.decode(
            bytes((2, 9, 0, 255, 255, 255, 255, 255, 255, 255, 255))
        ) == (0xffffffffffffffff, b'')

    def testNegLong(self):
        assert decoder.decode(
            bytes((2, 9, 255, 0, 0, 0, 0, 0, 0, 0, 1))
        ) == (-0xffffffffffffffff, b'')

    def testSpec(self):
        try:
            decoder.decode(
                bytes((2, 1, 12)), asn1Spec=univ.Null()
            ) == (12, b'')
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong asn1Spec worked out'
        assert decoder.decode(
            bytes((2, 1, 12)), asn1Spec=univ.Integer()
        ) == (12, b'')

    def testTagFormat(self):
        try:
            decoder.decode(bytes((34, 1, 12)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong tagFormat worked out'


class BooleanDecoderTestCase(BaseTestCase):
    def testTrue(self):
        assert decoder.decode(bytes((1, 1, 1))) == (1, b'')

    def testTrueNeg(self):
        assert decoder.decode(bytes((1, 1, 255))) == (1, b'')

    def testExtraTrue(self):
        assert decoder.decode(bytes((1, 1, 1, 0, 120, 50, 50))) == (1, bytes((0, 120, 50, 50)))

    def testFalse(self):
        assert decoder.decode(bytes((1, 1, 0))) == (0, b'')

    def testTagFormat(self):
        try:
            decoder.decode(bytes((33, 1, 1)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong tagFormat worked out'


class BitStringDecoderTestCase(BaseTestCase):
    def testDefMode(self):
        assert decoder.decode(
            bytes((3, 3, 1, 169, 138))
        ) == ((1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1), b'')

    def testIndefMode(self):
        assert decoder.decode(
            bytes((3, 3, 1, 169, 138))
        ) == ((1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1), b'')

    def testDefModeChunked(self):
        assert decoder.decode(
            bytes((35, 8, 3, 2, 0, 169, 3, 2, 1, 138))
        ) == ((1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1), b'')

    def testIndefModeChunked(self):
        assert decoder.decode(
            bytes((35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0))
        ) == ((1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1), b'')

    def testDefModeChunkedSubst(self):
        assert decoder.decode(
            bytes((35, 8, 3, 2, 0, 169, 3, 2, 1, 138)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes((3, 2, 0, 169, 3, 2, 1, 138)), b'')

    def testDefModeChunkedSubstV04(self):
        assert decoder.decode(
            bytes((35, 8, 3, 2, 0, 169, 3, 2, 1, 138)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes((3, 2, 0, 169, 3, 2, 1, 138)), b'')

    def testIndefModeChunkedSubst(self):
        assert decoder.decode(
            bytes((35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes((3, 2, 0, 169, 3, 2, 1, 138, 0, 0)), b'')

    def testIndefModeChunkedSubstV04(self):
        assert decoder.decode(
            bytes((35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes((3, 2, 0, 169, 3, 2, 1, 138, 0, 0)), b'')

    def testTypeChecking(self):
        try:
            decoder.decode(bytes((35, 4, 2, 2, 42, 42)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'accepted mis-encoded bit-string constructed out of an integer'


class OctetStringDecoderTestCase(BaseTestCase):
    def testDefMode(self):
        assert decoder.decode(
            bytes((4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120))
        ) == (b'Quick brown fox', b'')

    def testIndefMode(self):
        assert decoder.decode(
            bytes((36, 128, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120, 0, 0))
        ) == (b'Quick brown fox', b'')

    def testDefModeChunked(self):
        assert decoder.decode(
            bytes(
                (36, 23, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120))
        ) == (b'Quick brown fox', b'')

    def testIndefModeChunked(self):
        assert decoder.decode(
            bytes((36, 128, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120, 0, 0))
        ) == (b'Quick brown fox', b'')

    def testDefModeChunkedSubst(self):
        assert decoder.decode(
            bytes(
                (36, 23, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes((4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120)), b'')

    def testDefModeChunkedSubstV04(self):
        assert decoder.decode(
            bytes(
                (36, 23, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes((4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120)), b'')

    def testIndefModeChunkedSubst(self):
        assert decoder.decode(
            bytes((36, 128, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111,
                       120, 0, 0)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes(
            (4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120, 0, 0)), b'')

    def testIndefModeChunkedSubstV04(self):
        assert decoder.decode(
            bytes((36, 128, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111,
                       120, 0, 0)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes(
            (4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120, 0, 0)), b'')


class ExpTaggedOctetStringDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.o = univ.OctetString(
            'Quick brown fox',
            tagSet=univ.OctetString.tagSet.tagExplicitly(
                tag.Tag(tag.tagClassApplication, tag.tagFormatSimple, 5)
            ))

    def testDefMode(self):
        o, r = decoder.decode(
            bytes((101, 17, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120))
        )
        assert not r
        assert self.o == o
        assert self.o.tagSet == o.tagSet
        assert self.o.isSameTypeWith(o)

    def testIndefMode(self):
        o, r = decoder.decode(
            bytes((101, 128, 36, 128, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120, 0, 0, 0, 0))
        )
        assert not r
        assert self.o == o
        assert self.o.tagSet == o.tagSet
        assert self.o.isSameTypeWith(o)

    def testDefModeChunked(self):
        o, r = decoder.decode(
            bytes((101, 25, 36, 23, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120))
        )
        assert not r
        assert self.o == o
        assert self.o.tagSet == o.tagSet
        assert self.o.isSameTypeWith(o)

    def testIndefModeChunked(self):
        o, r = decoder.decode(
            bytes((101, 128, 36, 128, 4, 4, 81, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 4, 111, 119, 110, 32, 4, 3, 102, 111, 120, 0, 0, 0, 0))
        )
        assert not r
        assert self.o == o
        assert self.o.tagSet == o.tagSet
        assert self.o.isSameTypeWith(o)

    def testDefModeSubst(self):
        assert decoder.decode(
            bytes((101, 17, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes((4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120)), b'')

    def testDefModeSubstV04(self):
        assert decoder.decode(
            bytes((101, 17, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes((4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120)), b'')

    def testIndefModeSubst(self):
        assert decoder.decode(
            bytes((
                      101, 128, 36, 128, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120, 0,
                      0, 0, 0)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes(
            (36, 128, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120, 0, 0, 0, 0)), b'')

    def testIndefModeSubstV04(self):
        assert decoder.decode(
            bytes((
                      101, 128, 36, 128, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120, 0,
                      0, 0, 0)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes(
            (36, 128, 4, 15, 81, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 32, 102, 111, 120, 0, 0, 0, 0)), b'')


class NullDecoderTestCase(BaseTestCase):
    def testNull(self):
        assert decoder.decode(bytes((5, 0))) == (b'', b'')

    def testTagFormat(self):
        try:
            decoder.decode(bytes((37, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong tagFormat worked out'


# Useful analysis of OID encoding issues could be found here:
# https://misc.daniel-marschall.de/asn.1/oid_facts.html
class ObjectIdentifierDecoderTestCase(BaseTestCase):
    def testOne(self):
        assert decoder.decode(
            bytes((6, 6, 43, 6, 0, 191, 255, 126))
        ) == ((1, 3, 6, 0, 0xffffe), b'')

    def testEdge1(self):
        assert decoder.decode(
            bytes((6, 1, 39))
        ) == ((0, 39), b'')

    def testEdge2(self):
        assert decoder.decode(
            bytes((6, 1, 79))
        ) == ((1, 39), b'')

    def testEdge3(self):
        assert decoder.decode(
            bytes((6, 1, 120))
        ) == ((2, 40), b'')

    def testEdge4(self):
        assert decoder.decode(
            bytes((6, 5, 0x90, 0x80, 0x80, 0x80, 0x4F))
        ) == ((2, 0xffffffff), b'')

    def testEdge5(self):
        assert decoder.decode(
            bytes((6, 1, 0x7F))
        ) == ((2, 47), b'')

    def testEdge6(self):
        assert decoder.decode(
            bytes((6, 2, 0x81, 0x00))
        ) == ((2, 48), b'')

    def testEdge7(self):
        assert decoder.decode(
            bytes((6, 3, 0x81, 0x34, 0x03))
        ) == ((2, 100, 3), b'')

    def testEdge8(self):
        assert decoder.decode(
            bytes((6, 2, 133, 0))
        ) == ((2, 560), b'')

    def testEdge9(self):
        assert decoder.decode(
            bytes((6, 4, 0x88, 0x84, 0x87, 0x02))
        ) == ((2, 16843570), b'')

    def testNonLeading0x80(self):
        assert decoder.decode(
            bytes((6, 5, 85, 4, 129, 128, 0)),
        ) == ((2, 5, 4, 16384), b'')

    def testLeading0x80Case1(self):
        try:
            decoder.decode(
                bytes((6, 5, 85, 4, 128, 129, 0))
            )
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Leading 0x80 tolerated'

    def testLeading0x80Case2(self):
        try:
            decoder.decode(
                bytes((6, 7, 1, 0x80, 0x80, 0x80, 0x80, 0x80, 0x7F))
            )
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Leading 0x80 tolerated'

    def testLeading0x80Case3(self):
        try:
            decoder.decode(
                bytes((6, 2, 0x80, 1))
            )
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Leading 0x80 tolerated'

    def testLeading0x80Case4(self):
        try:
            decoder.decode(
                bytes((6, 2, 0x80, 0x7F))
            )
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Leading 0x80 tolerated'

    def testTagFormat(self):
        try:
            decoder.decode(bytes((38, 1, 239)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong tagFormat worked out'

    def testZeroLength(self):
        try:
            decoder.decode(bytes((6, 0, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'zero length tolerated'

    def testIndefiniteLength(self):
        try:
            decoder.decode(bytes((6, 128, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'indefinite length tolerated'

    def testReservedLength(self):
        try:
            decoder.decode(bytes((6, 255, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'reserved length tolerated'

    def testLarge1(self):
        assert decoder.decode(
            bytes((0x06, 0x11, 0x83, 0xC6, 0xDF, 0xD4, 0xCC, 0xB3, 0xFF, 0xFF, 0xFE, 0xF0, 0xB8, 0xD6, 0xB8, 0xCB, 0xE2, 0xB7, 0x17))
        ) == ((2, 18446744073709551535184467440737095), b'')

    def testLarge2(self):
        assert decoder.decode(
            bytes((0x06, 0x13, 0x88, 0x37, 0x83, 0xC6, 0xDF, 0xD4, 0xCC, 0xB3, 0xFF, 0xFF, 0xFE, 0xF0, 0xB8, 0xD6, 0xB8, 0xCB, 0xE2, 0xB6, 0x47))
        ) == ((2, 999, 18446744073709551535184467440737095), b'')

    def testExcessiveContinuationOctets(self):
        """Test that OID arcs with excessive continuation octets are rejected."""
        # Create a payload with 25 continuation octets (exceeds 20 limit)
        # 0x81 bytes are continuation octets, 0x01 terminates
        malicious_payload = bytes([0x06, 26]) + bytes([0x81] * 25) + bytes([0x01])
        try:
            decoder.decode(malicious_payload)
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Excessive continuation octets tolerated'

    def testMaxAllowedContinuationOctets(self):
        """Test that OID arcs at the maximum continuation octets limit work."""
        # Create a payload with exactly 20 continuation octets (at limit)
        # This should succeed
        payload = bytes([0x06, 21]) + bytes([0x81] * 20) + bytes([0x01])
        try:
            decoder.decode(payload)
        except error.PyAsn1Error:
            assert 0, 'Valid OID with 20 continuation octets rejected'

    def testOneOverContinuationLimit(self):
        """Test boundary: 21 continuation octets (one over limit) is rejected."""
        payload = bytes([0x06, 22]) + bytes([0x81] * 21) + bytes([0x01])
        try:
            decoder.decode(payload)
        except error.PyAsn1Error:
            pass
        else:
            assert 0, '21 continuation octets tolerated (should be rejected)'

    def testExcessiveContinuationInSecondArc(self):
        """Test that limit applies to subsequent arcs, not just the first."""
        # First arc: valid simple byte (0x55 = 85, decodes to arc 2.5)
        # Second arc: excessive continuation octets
        payload = bytes([0x06, 27]) + bytes([0x55]) + bytes([0x81] * 25) + bytes([0x01])
        try:
            decoder.decode(payload)
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Excessive continuation in second arc tolerated'

    def testMultipleArcsAtLimit(self):
        """Test multiple arcs each at the continuation limit work correctly."""
        # Two arcs, each with 20 continuation octets (both at limit)
        arc1 = bytes([0x81] * 20) + bytes([0x01])  # 21 bytes
        arc2 = bytes([0x81] * 20) + bytes([0x01])  # 21 bytes
        payload = bytes([0x06, 42]) + arc1 + arc2
        try:
            decoder.decode(payload)
        except error.PyAsn1Error:
            assert 0, 'Multiple valid arcs at limit rejected'

    def testExcessiveContinuationWithMaxBytes(self):
        """Test with 0xFF continuation bytes (maximum value, not just 0x81)."""
        # 0xFF bytes are also continuation octets (high bit set)
        malicious_payload = bytes([0x06, 26]) + bytes([0xFF] * 25) + bytes([0x01])
        try:
            decoder.decode(malicious_payload)
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Excessive 0xFF continuation octets tolerated'


class RelativeOIDDecoderTestCase(BaseTestCase):
    def testOne(self):
        obj, rest = decoder.decode(bytes((13, 1, 39)))
        assert str(obj) == '39'
        assert rest == b''

    def testTwo(self):
        assert decoder.decode(
            bytes((13, 2, 5, 6))
        ) == ((5, 6), b'')

    def testThree(self):
        assert decoder.decode(
            bytes((13, 3, 5, 6, 7))
        ) == ((5, 6, 7), b'')

    def testNonLeading0x80(self):
        assert decoder.decode(
            bytes((13, 5, 85, 4, 129, 128, 0)),
        ) == ((85, 4, 16384), b'')

    def testLeading0x80(self):
        try:
            decoder.decode(
                bytes((13, 5, 85, 4, 128, 129, 0))
            )
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Leading 0x80 tolerated'

    def testTagFormat(self):
        try:
            decoder.decode(bytes((38, 1, 239)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong tagFormat worked out'

    def testZeroLength(self):
        try:
            decoder.decode(bytes((13, 0, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'zero length tolerated'

    def testIndefiniteLength(self):
        try:
            decoder.decode(bytes((13, 128, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'indefinite length tolerated'

    def testReservedLength(self):
        try:
            decoder.decode(bytes((13, 255, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'reserved length tolerated'

    def testLarge(self):
        assert decoder.decode(
            bytes((0x0D, 0x13, 0x88, 0x37, 0x83, 0xC6, 0xDF, 0xD4, 0xCC, 0xB3, 0xFF, 0xFF, 0xFE, 0xF0, 0xB8, 0xD6, 0xB8, 0xCB, 0xE2, 0xB6, 0x47))
        ) == ((1079, 18446744073709551535184467440737095), b'')

    def testExcessiveContinuationOctets(self):
        """Test that RELATIVE-OID arcs with excessive continuation octets are rejected."""
        # Create a payload with 25 continuation octets (exceeds 20 limit)
        malicious_payload = bytes([0x0D, 26]) + bytes([0x81] * 25) + bytes([0x01])
        try:
            decoder.decode(malicious_payload)
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Excessive continuation octets tolerated'

    def testMaxAllowedContinuationOctets(self):
        """Test that RELATIVE-OID arcs at the maximum continuation octets limit work."""
        # Create a payload with exactly 20 continuation octets (at limit)
        payload = bytes([0x0D, 21]) + bytes([0x81] * 20) + bytes([0x01])
        try:
            decoder.decode(payload)
        except error.PyAsn1Error:
            assert 0, 'Valid RELATIVE-OID with 20 continuation octets rejected'

    def testOneOverContinuationLimit(self):
        """Test boundary: 21 continuation octets (one over limit) is rejected."""
        payload = bytes([0x0D, 22]) + bytes([0x81] * 21) + bytes([0x01])
        try:
            decoder.decode(payload)
        except error.PyAsn1Error:
            pass
        else:
            assert 0, '21 continuation octets tolerated (should be rejected)'

    def testExcessiveContinuationInSecondArc(self):
        """Test that limit applies to subsequent arcs, not just the first."""
        # First arc: valid simple byte
        # Second arc: excessive continuation octets
        payload = bytes([0x0D, 27]) + bytes([0x55]) + bytes([0x81] * 25) + bytes([0x01])
        try:
            decoder.decode(payload)
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Excessive continuation in second arc tolerated'

    def testMultipleArcsAtLimit(self):
        """Test multiple arcs each at the continuation limit work correctly."""
        # Two arcs, each with 20 continuation octets (both at limit)
        arc1 = bytes([0x81] * 20) + bytes([0x01])  # 21 bytes
        arc2 = bytes([0x81] * 20) + bytes([0x01])  # 21 bytes
        payload = bytes([0x0D, 42]) + arc1 + arc2
        try:
            decoder.decode(payload)
        except error.PyAsn1Error:
            assert 0, 'Multiple valid arcs at limit rejected'

    def testExcessiveContinuationWithMaxBytes(self):
        """Test with 0xFF continuation bytes (maximum value, not just 0x81)."""
        # 0xFF bytes are also continuation octets (high bit set)
        malicious_payload = bytes([0x0D, 26]) + bytes([0xFF] * 25) + bytes([0x01])
        try:
            decoder.decode(malicious_payload)
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'Excessive 0xFF continuation octets tolerated'


class RealDecoderTestCase(BaseTestCase):
    def testChar(self):
        assert decoder.decode(
            bytes((9, 7, 3, 49, 50, 51, 69, 49, 49))
        ) == (univ.Real((123, 10, 11)), b'')

    def testBin1(self):  # check base = 2
        assert decoder.decode(  # (0.5, 2, 0) encoded with base = 2
            bytes((9, 3, 128, 255, 1))
        ) == (univ.Real((1, 2, -1)), b'')

    def testBin2(self):  # check base = 2 and scale factor
        assert decoder.decode(  # (3.25, 2, 0) encoded with base = 8
            bytes((9, 3, 148, 255, 13))
        ) == (univ.Real((26, 2, -3)), b'')

    def testBin3(self):  # check base = 16
        assert decoder.decode(  # (0.00390625, 2, 0) encoded with base = 16
            bytes((9, 3, 160, 254, 1))
        ) == (univ.Real((1, 2, -8)), b'')

    def testBin4(self):  # check exponent = 0
        assert decoder.decode(  # (1, 2, 0) encoded with base = 2
            bytes((9, 3, 128, 0, 1))
        ) == (univ.Real((1, 2, 0)), b'')

    def testBin5(self):  # case of 2 octs for exponent and negative exponent
        assert decoder.decode(  # (3, 2, -1020) encoded with base = 16
            bytes((9, 4, 161, 255, 1, 3))
        ) == (univ.Real((3, 2, -1020)), b'')

# TODO: this requires Real type comparison fix

#    def testBin6(self):
#        assert decoder.decode(
#            bytes((9, 5, 162, 0, 255, 255, 1))
#        ) == (univ.Real((1, 2, 262140)), b'')

#    def testBin7(self):
#        assert decoder.decode(
#            bytes((9, 7, 227, 4, 1, 35, 69, 103, 1))
#        ) == (univ.Real((-1, 2, 76354972)), b'')

    def testPlusInf(self):
        assert decoder.decode(
            bytes((9, 1, 64))
        ) == (univ.Real('inf'), b'')

    def testMinusInf(self):
        assert decoder.decode(
            bytes((9, 1, 65))
        ) == (univ.Real('-inf'), b'')

    def testEmpty(self):
        assert decoder.decode(
            bytes((9, 0))
        ) == (univ.Real(0.0), b'')

    def testTagFormat(self):
        try:
            decoder.decode(bytes((41, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong tagFormat worked out'

    def testShortEncoding(self):
        try:
            decoder.decode(bytes((9, 1, 131)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'accepted too-short real'


class UniversalStringDecoderTestCase(BaseTestCase):
    def testDecoder(self):
        assert decoder.decode(bytes((28, 12, 0, 0, 0, 97, 0, 0, 0, 98, 0, 0, 0, 99))) == (char.UniversalString('abc'), b'')


class BMPStringDecoderTestCase(BaseTestCase):
    def testDecoder(self):
        assert decoder.decode(bytes((30, 6, 0, 97, 0, 98, 0, 99))) == (char.BMPString('abc'), b'')


class UTF8StringDecoderTestCase(BaseTestCase):
    def testDecoder(self):
        assert decoder.decode(bytes((12, 3, 97, 98, 99))) == (char.UTF8String('abc'), b'')


class SequenceOfDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        self.s = univ.SequenceOf(componentType=univ.OctetString())
        self.s.setComponentByPosition(0, univ.OctetString('quick brown'))

    def testDefMode(self):
        assert decoder.decode(
            bytes((48, 13, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110))
        ) == (self.s, b'')

    def testIndefMode(self):
        assert decoder.decode(
            bytes((48, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0))
        ) == (self.s, b'')

    def testDefModeChunked(self):
        assert decoder.decode(
            bytes((48, 19, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110))
        ) == (self.s, b'')

    def testIndefModeChunked(self):
        assert decoder.decode(
            bytes((48, 128, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 0, 0))
        ) == (self.s, b'')

    def testSchemalessDecoder(self):
        assert decoder.decode(
            bytes((48, 13, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=univ.SequenceOf()
        ) == (self.s, b'')


class ExpTaggedSequenceOfDecoderTestCase(BaseTestCase):

    def testWithSchema(self):
        s = univ.SequenceOf().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))
        s2, r = decoder.decode(
            bytes((163, 15, 48, 13, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=s
        )
        assert not r
        assert s2 == [b'quick brown']
        assert s.tagSet == s2.tagSet

    def testWithoutSchema(self):
        s = univ.SequenceOf().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))
        s2, r = decoder.decode(
            bytes((163, 15, 48, 13, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110))
        )
        assert not r
        assert s2 == [b'quick brown']
        assert s.tagSet == s2.tagSet


class SequenceOfDecoderWithSchemaTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.SequenceOf(componentType=univ.OctetString())
        self.s.setComponentByPosition(0, univ.OctetString('quick brown'))

    def testDefMode(self):
        assert decoder.decode(
            bytes((48, 13, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=self.s
        ) == (self.s, b'')

    def testIndefMode(self):
        assert decoder.decode(
            bytes((48, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testDefModeChunked(self):
        assert decoder.decode(
            bytes((48, 19, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110)), asn1Spec=self.s
        ) == (self.s, b'')

    def testIndefModeChunked(self):
        assert decoder.decode(
            bytes((48, 128, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')


class SetOfDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.SetOf(componentType=univ.OctetString())
        self.s.setComponentByPosition(0, univ.OctetString('quick brown'))

    def testDefMode(self):
        assert decoder.decode(
            bytes((49, 13, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110))
        ) == (self.s, b'')

    def testIndefMode(self):
        assert decoder.decode(
            bytes((49, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0))
        ) == (self.s, b'')

    def testDefModeChunked(self):
        assert decoder.decode(
            bytes((49, 19, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110))
        ) == (self.s, b'')

    def testIndefModeChunked(self):
        assert decoder.decode(
            bytes((49, 128, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 0, 0))
        ) == (self.s, b'')

    def testSchemalessDecoder(self):
        assert decoder.decode(
            bytes((49, 13, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=univ.SetOf()
        ) == (self.s, b'')


class SetOfDecoderWithSchemaTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.SetOf(componentType=univ.OctetString())
        self.s.setComponentByPosition(0, univ.OctetString('quick brown'))

    def testDefMode(self):
        assert decoder.decode(
            bytes((49, 13, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=self.s
        ) == (self.s, b'')

    def testIndefMode(self):
        assert decoder.decode(
            bytes((49, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testDefModeChunked(self):
        assert decoder.decode(
            bytes((49, 19, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110)), asn1Spec=self.s
        ) == (self.s, b'')

    def testIndefModeChunked(self):
        assert decoder.decode(
            bytes((49, 128, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')


class SequenceDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null(b'')),
                namedtype.NamedType('first-name', univ.OctetString(b'')),
                namedtype.NamedType('age', univ.Integer(33))
            )
        )
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(1, univ.OctetString('quick brown'))
        self.s.setComponentByPosition(2, univ.Integer(1))

    def testWithOptionalAndDefaultedDefMode(self):
        assert decoder.decode(
            bytes((48, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1))
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefMode(self):
        assert decoder.decode(
            bytes((48, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0))
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefModeChunked(self):
        assert decoder.decode(
            bytes(
                (48, 24, 5, 0, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 2, 1, 1))
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefModeChunked(self):
        assert decoder.decode(
            bytes((48, 128, 5, 0, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0))
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefModeSubst(self):
        assert decoder.decode(
            bytes((48, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes((5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)), b'')

    def testWithOptionalAndDefaultedDefModeSubstV04(self):
        assert decoder.decode(
            bytes((48, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes((5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)), b'')

    def testWithOptionalAndDefaultedIndefModeSubst(self):
        assert decoder.decode(
            bytes((48, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes(
            (5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)), b'')

    def testWithOptionalAndDefaultedIndefModeSubstV04(self):
        assert decoder.decode(
            bytes((48, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes(
            (5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)), b'')

    def testTagFormat(self):
        try:
            decoder.decode(
                bytes((16, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1))
            )
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong tagFormat worked out'


class SequenceDecoderWithSchemaTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null(b'')),
                namedtype.OptionalNamedType('first-name', univ.OctetString()),
                namedtype.DefaultedNamedType('age', univ.Integer(33)),
            )
        )

    def __init(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(b''))

    def __initWithOptional(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(1, univ.OctetString('quick brown'))

    def __initWithDefaulted(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(2, univ.Integer(1))

    def __initWithOptionalAndDefaulted(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(1, univ.OctetString('quick brown'))
        self.s.setComponentByPosition(2, univ.Integer(1))

    def testDefMode(self):
        self.__init()
        assert decoder.decode(
            bytes((48, 2, 5, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testIndefMode(self):
        self.__init()
        assert decoder.decode(
            bytes((48, 128, 5, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testDefModeChunked(self):
        self.__init()
        assert decoder.decode(
            bytes((48, 2, 5, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testIndefModeChunked(self):
        self.__init()
        assert decoder.decode(
            bytes((48, 128, 5, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalDefMode(self):
        self.__initWithOptional()
        assert decoder.decode(
            bytes((48, 15, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionaIndefMode(self):
        self.__initWithOptional()
        assert decoder.decode(
            bytes((48, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 0, 0)),
            asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalDefModeChunked(self):
        self.__initWithOptional()
        assert decoder.decode(
            bytes((48, 21, 5, 0, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110)),
            asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalIndefModeChunked(self):
        self.__initWithOptional()
        assert decoder.decode(
            bytes((48, 128, 5, 0, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0,
                       0, 0, 0)),
            asn1Spec=self.s
        ) == (self.s, b'')

    def testWithDefaultedDefMode(self):
        self.__initWithDefaulted()
        assert decoder.decode(
            bytes((48, 5, 5, 0, 2, 1, 1)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithDefaultedIndefMode(self):
        self.__initWithDefaulted()
        assert decoder.decode(
            bytes((48, 128, 5, 0, 2, 1, 1, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithDefaultedDefModeChunked(self):
        self.__initWithDefaulted()
        assert decoder.decode(
            bytes((48, 5, 5, 0, 2, 1, 1)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithDefaultedIndefModeChunked(self):
        self.__initWithDefaulted()
        assert decoder.decode(
            bytes((48, 128, 5, 0, 2, 1, 1, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefMode(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((48, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)),
            asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefMode(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((48, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1,
                       0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefModeChunked(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes(
                (48, 24, 5, 0, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 2, 1, 1)),
            asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefModeChunked(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((48, 128, 5, 0, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0,
                       0, 2, 1, 1, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')


class SequenceDecoderWithUntaggedOpenTypesTestCase(BaseTestCase):
    def setUp(self):
        openType = opentype.OpenType(
            'id',
            {1: univ.Integer(),
             2: univ.OctetString()}
        )
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()),
                namedtype.NamedType('blob', univ.Any(), openType=openType)
            )
        )

    def testDecodeOpenTypesChoiceOne(self):
        s, r = decoder.decode(
            bytes((48, 6, 2, 1, 1, 2, 1, 12)), asn1Spec=self.s,
            decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 1
        assert s[1] == 12

    def testDecodeOpenTypesChoiceTwo(self):
        s, r = decoder.decode(
            bytes((48, 16, 2, 1, 2, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=self.s,
            decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 2
        assert s[1] == univ.OctetString('quick brown')

    def testDecodeOpenTypesUnknownType(self):
        try:
            s, r = decoder.decode(
                bytes((48, 6, 2, 1, 2, 6, 1, 39)), asn1Spec=self.s,
                decodeOpenTypes=True
            )

        except error.PyAsn1Error:
            pass

        else:
            assert False, 'unknown open type tolerated'

    def testDecodeOpenTypesUnknownId(self):
        s, r = decoder.decode(
            bytes((48, 6, 2, 1, 3, 6, 1, 39)), asn1Spec=self.s,
            decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 3
        assert s[1] == univ.OctetString(hexValue='060127')

    def testDontDecodeOpenTypesChoiceOne(self):
        s, r = decoder.decode(
            bytes((48, 6, 2, 1, 1, 2, 1, 12)), asn1Spec=self.s
        )
        assert not r
        assert s[0] == 1
        assert s[1] == bytes((2, 1, 12))

    def testDontDecodeOpenTypesChoiceTwo(self):
        s, r = decoder.decode(
            bytes((48, 16, 2, 1, 2, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=self.s
        )
        assert not r
        assert s[0] == 2
        assert s[1] == bytes((4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110))


class SequenceDecoderWithImplicitlyTaggedOpenTypesTestCase(BaseTestCase):
    def setUp(self):
        openType = opentype.OpenType(
            'id',
            {1: univ.Integer(),
             2: univ.OctetString()}
        )
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()),
                namedtype.NamedType(
                    'blob', univ.Any().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)), openType=openType
                )
            )
        )

    def testDecodeOpenTypesChoiceOne(self):
        s, r = decoder.decode(
            bytes((48, 8, 2, 1, 1, 131, 3, 2, 1, 12)), asn1Spec=self.s, decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 1
        assert s[1] == 12

    def testDecodeOpenTypesUnknownId(self):
        s, r = decoder.decode(
            bytes((48, 8, 2, 1, 3, 131, 3, 2, 1, 12)), asn1Spec=self.s, decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 3
        assert s[1] == univ.OctetString(hexValue='02010C')


class SequenceDecoderWithExplicitlyTaggedOpenTypesTestCase(BaseTestCase):
    def setUp(self):
        openType = opentype.OpenType(
            'id',
            {1: univ.Integer(),
             2: univ.OctetString()}
        )
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()),
                namedtype.NamedType(
                    'blob', univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)), openType=openType
                )
            )
        )

    def testDecodeOpenTypesChoiceOne(self):
        s, r = decoder.decode(
            bytes((48, 8, 2, 1, 1, 163, 3, 2, 1, 12)), asn1Spec=self.s, decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 1
        assert s[1] == 12

    def testDecodeOpenTypesUnknownId(self):
        s, r = decoder.decode(
            bytes((48, 8, 2, 1, 3, 163, 3, 2, 1, 12)), asn1Spec=self.s, decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 3
        assert s[1] == univ.OctetString(hexValue='02010C')


class SequenceDecoderWithUnaggedSetOfOpenTypesTestCase(BaseTestCase):
    def setUp(self):
        openType = opentype.OpenType(
            'id',
            {1: univ.Integer(),
             2: univ.OctetString()}
        )
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()),
                namedtype.NamedType('blob', univ.SetOf(componentType=univ.Any()),
                                    openType=openType)
            )
        )

    def testDecodeOpenTypesChoiceOne(self):
        s, r = decoder.decode(
            bytes((48, 8, 2, 1, 1, 49, 3, 2, 1, 12)), asn1Spec=self.s,
            decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 1
        assert s[1][0] == 12

    def testDecodeOpenTypesChoiceTwo(self):
        s, r = decoder.decode(
            bytes((48, 18, 2, 1, 2, 49, 13, 4, 11, 113, 117, 105, 99,
                       107, 32, 98, 114, 111, 119, 110)), asn1Spec=self.s,
            decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 2
        assert s[1][0] == univ.OctetString('quick brown')

    def testDecodeOpenTypesUnknownType(self):
        try:
            s, r = decoder.decode(
                bytes((48, 6, 2, 1, 2, 6, 1, 39)), asn1Spec=self.s,
                decodeOpenTypes=True
            )

        except error.PyAsn1Error:
            pass

        else:
            assert False, 'unknown open type tolerated'

    def testDecodeOpenTypesUnknownId(self):
        s, r = decoder.decode(
            bytes((48, 8, 2, 1, 3, 49, 3, 2, 1, 12)), asn1Spec=self.s,
            decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 3
        assert s[1][0] == univ.OctetString(hexValue='02010c')

    def testDontDecodeOpenTypesChoiceOne(self):
        s, r = decoder.decode(
            bytes((48, 8, 2, 1, 1, 49, 3, 2, 1, 12)), asn1Spec=self.s
        )
        assert not r
        assert s[0] == 1
        assert s[1][0] == bytes((2, 1, 12))

    def testDontDecodeOpenTypesChoiceTwo(self):
        s, r = decoder.decode(
            bytes((48, 18, 2, 1, 2, 49, 13, 4, 11, 113, 117, 105, 99,
                       107, 32, 98, 114, 111, 119, 110)), asn1Spec=self.s
        )
        assert not r
        assert s[0] == 2
        assert s[1][0] == bytes((4, 11, 113, 117, 105, 99, 107, 32, 98, 114,
                                     111, 119, 110))


class SequenceDecoderWithImplicitlyTaggedSetOfOpenTypesTestCase(BaseTestCase):
    def setUp(self):
        openType = opentype.OpenType(
            'id',
            {1: univ.Integer(),
             2: univ.OctetString()}
        )
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()),
                namedtype.NamedType(
                    'blob', univ.SetOf(
                        componentType=univ.Any().subtype(
                            implicitTag=tag.Tag(
                                tag.tagClassContext, tag.tagFormatSimple, 3))),
                    openType=openType
                )
            )
        )

    def testDecodeOpenTypesChoiceOne(self):
        s, r = decoder.decode(
            bytes((48, 10, 2, 1, 1, 49, 5, 131, 3, 2, 1, 12)),
            asn1Spec=self.s, decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 1
        assert s[1][0] == 12

    def testDecodeOpenTypesUnknownId(self):
        s, r = decoder.decode(
            bytes((48, 10, 2, 1, 3, 49, 5, 131, 3, 2, 1, 12)),
            asn1Spec=self.s, decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 3
        assert s[1][0] == univ.OctetString(hexValue='02010C')


class SequenceDecoderWithExplicitlyTaggedSetOfOpenTypesTestCase(BaseTestCase):
    def setUp(self):
        openType = opentype.OpenType(
            'id',
            {1: univ.Integer(),
             2: univ.OctetString()}
        )
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()),
                namedtype.NamedType(
                    'blob', univ.SetOf(
                        componentType=univ.Any().subtype(
                            explicitTag=tag.Tag(
                                tag.tagClassContext, tag.tagFormatSimple, 3))),
                    openType=openType
                )
            )
        )

    def testDecodeOpenTypesChoiceOne(self):
        s, r = decoder.decode(
            bytes((48, 10, 2, 1, 1, 49, 5, 131, 3, 2, 1, 12)),
            asn1Spec=self.s, decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 1
        assert s[1][0] == 12

    def testDecodeOpenTypesUnknownId(self):
        s, r = decoder.decode(
            bytes( (48, 10, 2, 1, 3, 49, 5, 131, 3, 2, 1, 12)),
            asn1Spec=self.s, decodeOpenTypes=True
        )
        assert not r
        assert s[0] == 3
        assert s[1][0] == univ.OctetString(hexValue='02010C')


class SetDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.Set(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null(b'')),
                namedtype.NamedType('first-name', univ.OctetString(b'')),
                namedtype.NamedType('age', univ.Integer(33))
            )
        )
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(1, univ.OctetString('quick brown'))
        self.s.setComponentByPosition(2, univ.Integer(1))

    def testWithOptionalAndDefaultedDefMode(self):
        assert decoder.decode(
            bytes((49, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1))
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefMode(self):
        assert decoder.decode(
            bytes((49, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0))
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefModeChunked(self):
        assert decoder.decode(
            bytes(
                (49, 24, 5, 0, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 2, 1, 1))
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefModeChunked(self):
        assert decoder.decode(
            bytes((49, 128, 5, 0, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0))
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefModeSubst(self):
        assert decoder.decode(
            bytes((49, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes((5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)), b'')

    def testWithOptionalAndDefaultedDefModeSubstV04(self):
        assert decoder.decode(
            bytes((49, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes((5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)), b'')

    def testWithOptionalAndDefaultedIndefModeSubst(self):
        assert decoder.decode(
            bytes((49, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)),
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes(
            (5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)), b'')

    def testWithOptionalAndDefaultedIndefModeSubstV04(self):
        assert decoder.decode(
            bytes((49, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)),
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes(
            (5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)), b'')

    def testTagFormat(self):
        try:
            decoder.decode(
                bytes((16, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1))
            )
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'wrong tagFormat worked out'


class SetDecoderWithSchemaTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.Set(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null(b'')),
                namedtype.OptionalNamedType('first-name', univ.OctetString()),
                namedtype.DefaultedNamedType('age', univ.Integer(33)),
            )
        )

    def __init(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(b''))

    def __initWithOptional(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(1, univ.OctetString('quick brown'))

    def __initWithDefaulted(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(2, univ.Integer(1))

    def __initWithOptionalAndDefaulted(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(1, univ.OctetString('quick brown'))
        self.s.setComponentByPosition(2, univ.Integer(1))

    def testDefMode(self):
        self.__init()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testIndefMode(self):
        self.__init()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testDefModeChunked(self):
        self.__init()
        assert decoder.decode(
            bytes((49, 2, 5, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testIndefModeChunked(self):
        self.__init()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalDefMode(self):
        self.__initWithOptional()
        assert decoder.decode(
            bytes((49, 15, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalIndefMode(self):
        self.__initWithOptional()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalDefModeChunked(self):
        self.__initWithOptional()
        assert decoder.decode(
            bytes((49, 21, 5, 0, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalIndefModeChunked(self):
        self.__initWithOptional()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithDefaultedDefMode(self):
        self.__initWithDefaulted()
        assert decoder.decode(
            bytes((49, 5, 5, 0, 2, 1, 1)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithDefaultedIndefMode(self):
        self.__initWithDefaulted()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 2, 1, 1, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithDefaultedDefModeChunked(self):
        self.__initWithDefaulted()
        assert decoder.decode(
            bytes((49, 5, 5, 0, 2, 1, 1)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithDefaultedIndefModeChunked(self):
        self.__initWithDefaulted()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 2, 1, 1, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefMode(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((49, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefModeReordered(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((49, 18, 2, 1, 1, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 5, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefMode(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefModeReordered(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((49, 128, 2, 1, 1, 5, 0, 36, 128, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 0, 0,  0, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedDefModeChunked(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((49, 24, 5, 0, 36, 17, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 2, 1, 1)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithOptionalAndDefaultedIndefModeChunked(self):
        self.__initWithOptionalAndDefaulted()
        assert decoder.decode(
            bytes((49, 128, 5, 0, 36, 128, 4, 4, 113, 117, 105, 99, 4, 4, 107, 32, 98, 114, 4, 3, 111, 119, 110, 0, 0, 2, 1, 1, 0, 0)), asn1Spec=self.s
        ) == (self.s, b'')


class SequenceOfWithExpTaggedOctetStringDecoder(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.SequenceOf(
            componentType=univ.OctetString().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))
        )
        self.s.setComponentByPosition(0, 'q')
        self.s2 = univ.SequenceOf()

    def testDefModeSchema(self):
        s, r = decoder.decode(bytes((48, 5, 163, 3, 4, 1, 113)), asn1Spec=self.s)
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testIndefModeSchema(self):
        s, r = decoder.decode(bytes((48, 128, 163, 128, 4, 1, 113, 0, 0, 0, 0)), asn1Spec=self.s)
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testDefModeNoComponent(self):
        s, r = decoder.decode(bytes((48, 5, 163, 3, 4, 1, 113)), asn1Spec=self.s2)
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testIndefModeNoComponent(self):
        s, r = decoder.decode(bytes((48, 128, 163, 128, 4, 1, 113, 0, 0, 0, 0)), asn1Spec=self.s2)
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testDefModeSchemaless(self):
        s, r = decoder.decode(bytes((48, 5, 163, 3, 4, 1, 113)))
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testIndefModeSchemaless(self):
        s, r = decoder.decode(bytes((48, 128, 163, 128, 4, 1, 113, 0, 0, 0, 0)))
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet


class SequenceWithExpTaggedOctetStringDecoder(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType(
                    'x', univ.OctetString().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))
                )
            )
        )
        self.s.setComponentByPosition(0, 'q')
        self.s2 = univ.Sequence()

    def testDefModeSchema(self):
        s, r = decoder.decode(bytes((48, 5, 163, 3, 4, 1, 113)), asn1Spec=self.s)
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testIndefModeSchema(self):
        s, r = decoder.decode(bytes((48, 128, 163, 128, 4, 1, 113, 0, 0, 0, 0)), asn1Spec=self.s)
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testDefModeNoComponent(self):
        s, r = decoder.decode(bytes((48, 5, 163, 3, 4, 1, 113)), asn1Spec=self.s2)
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testIndefModeNoComponent(self):
        s, r = decoder.decode(bytes((48, 128, 163, 128, 4, 1, 113, 0, 0, 0, 0)), asn1Spec=self.s2)
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testDefModeSchemaless(self):
        s, r = decoder.decode(bytes((48, 5, 163, 3, 4, 1, 113)))
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet

    def testIndefModeSchemaless(self):
        s, r = decoder.decode(bytes((48, 128, 163, 128, 4, 1, 113, 0, 0, 0, 0)))
        assert not r
        assert s == self.s
        assert s.tagSet == self.s.tagSet


class ChoiceDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null(b'')),
                namedtype.NamedType('number', univ.Integer(0)),
                namedtype.NamedType('string', univ.OctetString())
            )
        )

    def testBySpec(self):
        self.s.setComponentByPosition(0, univ.Null(b''))
        assert decoder.decode(
            bytes((5, 0)), asn1Spec=self.s
        ) == (self.s, b'')

    def testWithoutSpec(self):
        self.s.setComponentByPosition(0, univ.Null(b''))
        assert decoder.decode(bytes((5, 0))) == (self.s, b'')
        assert decoder.decode(bytes((5, 0))) == (univ.Null(b''), b'')

    def testUndefLength(self):
        self.s.setComponentByPosition(2, univ.OctetString('abcdefgh'))
        assert decoder.decode(bytes((36, 128, 4, 3, 97, 98, 99, 4, 3, 100, 101, 102, 4, 2, 103, 104, 0, 0)),
                              asn1Spec=self.s) == (self.s, b'')

    def testExplicitTag(self):
        s = self.s.subtype(explicitTag=tag.Tag(tag.tagClassContext,
                                               tag.tagFormatConstructed, 4))
        s.setComponentByPosition(0, univ.Null(b''))
        assert decoder.decode(bytes((164, 2, 5, 0)), asn1Spec=s) == (s, b'')

    def testExplicitTagUndefLength(self):
        s = self.s.subtype(explicitTag=tag.Tag(tag.tagClassContext,
                                               tag.tagFormatConstructed, 4))
        s.setComponentByPosition(0, univ.Null(b''))
        assert decoder.decode(bytes((164, 128, 5, 0, 0, 0)), asn1Spec=s) == (s, b'')


class AnyDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.Any()

    def testByUntagged(self):
        assert decoder.decode(
            bytes((4, 3, 102, 111, 120)), asn1Spec=self.s
        ) == (univ.Any('\004\003fox'), b'')

    def testTaggedEx(self):
        s = univ.Any('\004\003fox').subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))
        assert decoder.decode(bytes((164, 5, 4, 3, 102, 111, 120)), asn1Spec=s) == (s, b'')

    def testTaggedIm(self):
        s = univ.Any('\004\003fox').subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))
        assert decoder.decode(bytes((132, 5, 4, 3, 102, 111, 120)), asn1Spec=s) == (s, b'')

    def testByUntaggedIndefMode(self):
        assert decoder.decode(
            bytes((4, 3, 102, 111, 120)), asn1Spec=self.s
        ) == (univ.Any('\004\003fox'), b'')

    def testTaggedExIndefMode(self):
        s = univ.Any('\004\003fox').subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))
        assert decoder.decode(bytes((164, 128, 4, 3, 102, 111, 120, 0, 0)), asn1Spec=s) == (s, b'')

    def testTaggedImIndefMode(self):
        s = univ.Any('\004\003fox').subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))
        assert decoder.decode(bytes((164, 128, 4, 3, 102, 111, 120, 0, 0)), asn1Spec=s) == (s, b'')

    def testByUntaggedSubst(self):
        assert decoder.decode(
            bytes((4, 3, 102, 111, 120)),
            asn1Spec=self.s,
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes((4, 3, 102, 111, 120)), b'')

    def testByUntaggedSubstV04(self):
        assert decoder.decode(
            bytes((4, 3, 102, 111, 120)),
            asn1Spec=self.s,
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes((4, 3, 102, 111, 120)), b'')

    def testTaggedExSubst(self):
        assert decoder.decode(
            bytes((164, 5, 4, 3, 102, 111, 120)),
            asn1Spec=self.s,
            substrateFun=lambda a, b, c, d: streaming.readFromStream(b, c)
        ) == (bytes((164, 5, 4, 3, 102, 111, 120)), b'')

    def testTaggedExSubstV04(self):
        assert decoder.decode(
            bytes((164, 5, 4, 3, 102, 111, 120)),
            asn1Spec=self.s,
            substrateFun=lambda a, b, c: (b, b[c:])
        ) == (bytes((164, 5, 4, 3, 102, 111, 120)), b'')


class EndOfOctetsTestCase(BaseTestCase):
    def testUnexpectedEoo(self):
        try:
            decoder.decode(bytes((0, 0)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'end-of-contents octets accepted at top level'

    def testExpectedEoo(self):
        result, remainder = decoder.decode(bytes((0, 0)), allowEoo=True)
        assert eoo.endOfOctets.isSameTypeWith(result) and result == eoo.endOfOctets and result is eoo.endOfOctets
        assert remainder == b''

    def testDefiniteNoEoo(self):
        try:
            decoder.decode(bytes((0x23, 0x02, 0x00, 0x00)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'end-of-contents octets accepted inside definite-length encoding'

    def testIndefiniteEoo(self):
        result, remainder = decoder.decode(bytes((0x23, 0x80, 0x00, 0x00)))
        assert result == () and remainder == b'', 'incorrect decoding of indefinite length end-of-octets'

    def testNoLongFormEoo(self):
        try:
            decoder.decode(bytes((0x23, 0x80, 0x00, 0x81, 0x00)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'end-of-contents octets accepted with invalid long-form length'

    def testNoConstructedEoo(self):
        try:
            decoder.decode(bytes((0x23, 0x80, 0x20, 0x00)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'end-of-contents octets accepted with invalid constructed encoding'

    def testNoEooData(self):
        try:
            decoder.decode(bytes((0x23, 0x80, 0x00, 0x01, 0x00)))
        except error.PyAsn1Error:
            pass
        else:
            assert 0, 'end-of-contents octets accepted with unexpected data'


class NonStringDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null(b'')),
                namedtype.NamedType('first-name', univ.OctetString(b'')),
                namedtype.NamedType('age', univ.Integer(33))
            )
        )
        self.s.setComponentByPosition(0, univ.Null(b''))
        self.s.setComponentByPosition(1, univ.OctetString('quick brown'))
        self.s.setComponentByPosition(2, univ.Integer(1))

        self.substrate = bytes([48, 18, 5, 0, 4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110, 2, 1, 1])

    def testOctetString(self):
        s = list(decoder.StreamingDecoder(
            univ.OctetString(self.substrate), asn1Spec=self.s))
        assert [self.s] == s

    def testAny(self):
        s = list(decoder.StreamingDecoder(
            univ.Any(self.substrate), asn1Spec=self.s))
        assert [self.s] == s


class ErrorOnDecodingTestCase(BaseTestCase):

    def testErrorCondition(self):
        decode = decoder.SingleItemDecoder(
            tagMap=decoder.TAG_MAP, typeMap=decoder.TYPE_MAP)
        substrate = bytes((00, 1, 2))
        stream = streaming.asSeekableStream(substrate)

        try:
            asn1Object = next(decode(stream))

        except error.PyAsn1Error:
            pass

        else:
            assert False, 'Unexpected decoder result %r' % (asn1Object,)

    def testRawDump(self):
        substrate = bytes((31, 8, 2, 1, 1, 131, 3, 2, 1, 12))
        stream = streaming.asSeekableStream(substrate)

        class SingleItemEncoder(decoder.SingleItemDecoder):
            defaultErrorState = decoder.stDumpRawValue

        class StreamingDecoder(decoder.StreamingDecoder):
            SINGLE_ITEM_DECODER = SingleItemEncoder

        class OneShotDecoder(decoder.Decoder):
            STREAMING_DECODER = StreamingDecoder

        d = OneShotDecoder()

        asn1Object, rest = d(stream)

        assert isinstance(asn1Object, univ.Any), (
            'Unexpected raw dump type %r' % (asn1Object,))
        assert asn1Object.asNumbers() == (31, 8, 2, 1, 1), (
            'Unexpected raw dump value %r' % (asn1Object,))
        assert rest == bytes((131, 3, 2, 1, 12)), (
            'Unexpected rest of substrate after raw dump %r' % rest)


class BinaryFileTestCase(BaseTestCase):
    """Assure that decode works on open binary files."""
    def testOneObject(self):
        _, path = tempfile.mkstemp()
        try:
            with open(path, "wb") as out:
                out.write(bytes((2, 1, 12)))

            with open(path, "rb") as source:
                values = list(decoder.StreamingDecoder(source))

            assert values == [12]
        finally:
            os.remove(path)

    def testMoreObjects(self):
        _, path = tempfile.mkstemp()
        try:
            with open(path, "wb") as out:
                out.write(bytes((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0)))

            with open(path, "rb") as source:
                values = list(decoder.StreamingDecoder(source))

            assert values == [12, (1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1)]

        finally:
            os.remove(path)

    def testInvalidFileContent(self):
        _, path = tempfile.mkstemp()
        try:
            with open(path, "wb") as out:
                out.write(bytes((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0, 7)))

            with open(path, "rb") as source:
                list(decoder.StreamingDecoder(source))

        except error.EndOfStreamError:
            pass

        finally:
            os.remove(path)


class BytesIOTestCase(BaseTestCase):
    def testRead(self):
        source = bytes((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0))
        stream = io.BytesIO(source)
        values = list(decoder.StreamingDecoder(stream))
        assert values == [12, (1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1)]


class BytearrayTestCase(BaseTestCase):
    def testRead(self):
        source = memoryview(bytes((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0)))
        values = list(decoder.StreamingDecoder(source))
        assert values == [12, (1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1)]


class MemoryviewTestCase(BaseTestCase):
    def testRead(self):
        source = bytearray((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0))
        values = list(decoder.StreamingDecoder(source))
        assert values == [12, (1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1)]


class UnicodeTestCase(BaseTestCase):
    def testFail(self):
        # This ensures that str objects cannot be parsed.
        source = bytes((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0)).decode("latin-1")
        try:
            next(decoder.StreamingDecoder(source))

        except error.UnsupportedSubstrateError:
            pass

        else:
            assert False, 'Tolerated parsing broken unicode strings'


class RestartableDecoderTestCase(BaseTestCase):

    class NonBlockingStream(io.BytesIO):
        block = False

        def read(self, size=-1):
            self.block = not self.block
            if self.block:
                return  # this is what non-blocking streams sometimes do

            return io.BytesIO.read(self, size)

    def setUp(self):
        BaseTestCase.setUp(self)

        self.s = univ.SequenceOf(componentType=univ.OctetString())
        self.s.setComponentByPosition(0, univ.OctetString('quick brown'))
        source = bytes(
            (48, 26,
             4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110,
             4, 11, 113, 117, 105, 99, 107, 32, 98, 114, 111, 119, 110))
        self.stream = self.NonBlockingStream(source)

    def testPartialReadingFromNonBlockingStream(self):
        iterator = iter(decoder.StreamingDecoder(self.stream, asn1Spec=self.s))

        res = next(iterator)

        assert isinstance(res, error.SubstrateUnderrunError)
        assert 'asn1Object' not in res.context

        res = next(iterator)

        assert isinstance(res, error.SubstrateUnderrunError)
        assert 'asn1Object' not in res.context

        res = next(iterator)

        assert isinstance(res, error.SubstrateUnderrunError)
        assert 'asn1Object' in res.context
        assert isinstance(res.context['asn1Object'], univ.SequenceOf)
        assert res.context['asn1Object'].isValue
        assert len(res.context['asn1Object']) == 0

        res = next(iterator)

        assert isinstance(res, error.SubstrateUnderrunError)
        assert 'asn1Object' in res.context
        assert isinstance(res.context['asn1Object'], univ.SequenceOf)
        assert res.context['asn1Object'].isValue
        assert len(res.context['asn1Object']) == 0

        res = next(iterator)

        assert isinstance(res, error.SubstrateUnderrunError)
        assert 'asn1Object' in res.context
        assert isinstance(res.context['asn1Object'], univ.SequenceOf)
        assert res.context['asn1Object'].isValue
        assert len(res.context['asn1Object']) == 0

        res = next(iterator)

        assert isinstance(res, error.SubstrateUnderrunError)
        assert 'asn1Object' in res.context
        assert isinstance(res.context['asn1Object'], univ.SequenceOf)
        assert res.context['asn1Object'].isValue
        assert len(res.context['asn1Object']) == 1

        res = next(iterator)

        assert isinstance(res, error.SubstrateUnderrunError)
        assert 'asn1Object' in res.context
        assert isinstance(res.context['asn1Object'], univ.SequenceOf)
        assert res.context['asn1Object'].isValue
        assert len(res.context['asn1Object']) == 1

        res = next(iterator)

        assert isinstance(res, error.SubstrateUnderrunError)
        assert 'asn1Object' in res.context
        assert isinstance(res.context['asn1Object'], univ.SequenceOf)
        assert res.context['asn1Object'].isValue
        assert len(res.context['asn1Object']) == 1

        res = next(iterator)

        assert isinstance(res, univ.SequenceOf)
        assert res.isValue
        assert len(res) == 2

        try:
            next(iterator)

        except StopIteration:
            pass

        else:
            assert False, 'End of stream not raised'


class CompressedFilesTestCase(BaseTestCase):
    def testGzip(self):
        _, path = tempfile.mkstemp(suffix=".gz")
        try:
            with gzip.open(path, "wb") as out:
                out.write(bytes((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0)))

            with gzip.open(path, "rb") as source:
                values = list(decoder.StreamingDecoder(source))

            assert values == [12, (1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1)]

        finally:
            os.remove(path)

    def testZipfile(self):
        # It is a seekable stream.
        _, path = tempfile.mkstemp(suffix=".zip")
        try:
            with zipfile.ZipFile(path, "w") as myzip:
                myzip.writestr("data", bytes((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0)))

            with zipfile.ZipFile(path, "r") as myzip:
                with myzip.open("data", "r") as source:
                    values = list(decoder.StreamingDecoder(source))
                    assert values == [12, (1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1)]
        finally:
            os.remove(path)

    def testZipfileMany(self):
        _, path = tempfile.mkstemp(suffix=".zip")
        try:
            with zipfile.ZipFile(path, "w") as myzip:
                #for i in range(100):
                myzip.writestr("data", bytes((2, 1, 12, 35, 128, 3, 2, 0, 169, 3, 2, 1, 138, 0, 0)) * 1000)

            with zipfile.ZipFile(path, "r") as myzip:
                with myzip.open("data", "r") as source:
                    values = list(decoder.StreamingDecoder(source))
                    assert values == [12, (1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1)] * 1000
        finally:
            os.remove(path)


class NonStreamingCompatibilityTestCase(BaseTestCase):
    def setUp(self):
        from pyasn1 import debug
        BaseTestCase.setUp(self)
        debug.setLogger(None)  # undo logger setup from BaseTestCase to work around unrelated issue

    def testPartialDecodeWithCustomSubstrateFun(self):
        snmp_req_substrate = bytes((
            0x30, 0x22, 0x02, 0x01, 0x01, 0x04, 0x06, 0x70, 0x75, 0x62, 0x6c, 0x69, 0x63, 0xa0, 0x15, 0x02, 0x04, 0x69,
            0x30, 0xdb, 0xeb, 0x02, 0x01, 0x00, 0x02, 0x01, 0x00, 0x30, 0x07, 0x30, 0x05, 0x06, 0x01, 0x01, 0x05, 0x00))
        seq, next_substrate = decoder.decode(
            snmp_req_substrate, asn1Spec=univ.Sequence(),
            recursiveFlag=False, substrateFun=lambda a, b, c: (a, b[:c])
        )
        assert seq.isSameTypeWith(univ.Sequence)
        assert next_substrate == snmp_req_substrate[2:]
        version, next_substrate = decoder.decode(
            next_substrate, asn1Spec=univ.Integer(), recursiveFlag=False,
            substrateFun=lambda a, b, c: (a, b[:c])
        )
        assert version == 1

    def testPartialDecodeWithDefaultSubstrateFun(self):
        substrate = bytes((
            0x04, 0x0e, 0x30, 0x0c, 0x06, 0x0a, 0x2b, 0x06, 0x01, 0x04, 0x01, 0x82, 0x37, 0x3c, 0x03, 0x02
        ))
        result, rest = decoder.decode(substrate, recursiveFlag=False)
        assert result.isSameTypeWith(univ.OctetString)
        assert rest == substrate[2:]

    def testPropagateUserException(self):
        substrate = io.BytesIO(bytes((0x04, 0x00)))

        def userSubstrateFun(_asn1Object, _substrate, _length, _options):
            raise TypeError("error inside user function")

        try:
            decoder.decode(substrate, asn1Spec=univ.OctetString, substrateFun=userSubstrateFun)
        except TypeError as exc:
            assert str(exc) == "error inside user function"
        else:
            raise AssertionError("decode() must not hide TypeError from inside user provided callback")


suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
