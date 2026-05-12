#!/usr/bin/env python

import codecs
import io
import unittest

import idna.codec

CODEC_NAME = "idna2008"


class IDNACodecTests(unittest.TestCase):
    def setUp(self):
        from . import test_idna

        self.idnatests = test_idna.IDNATests()
        self.idnatests.setUp()

    def testCodec(self):
        self.assertIs(codecs.lookup(CODEC_NAME).incrementalencoder, idna.codec.IncrementalEncoder)

    def testDirectDecode(self):
        self.idnatests.test_decode(decode=lambda obj: codecs.decode(obj, CODEC_NAME))

    def testIndirectDecode(self):
        self.idnatests.test_decode(decode=lambda obj: obj.decode(CODEC_NAME), skip_str=True)

    def testDirectEncode(self):
        self.idnatests.test_encode(encode=lambda obj: codecs.encode(obj, CODEC_NAME))

    def testIndirectEncode(self):
        self.idnatests.test_encode(encode=lambda obj: obj.encode(CODEC_NAME), skip_bytes=True)

    def testStreamReader(self):
        def decode(obj):
            if isinstance(obj, str):
                obj = bytes(obj, "ascii")
            buffer = io.BytesIO(obj)
            stream = codecs.getreader(CODEC_NAME)(buffer)
            return stream.read()

        return self.idnatests.test_decode(decode=decode, skip_str=True)

    def testStreamWriter(self):
        def encode(obj):
            buffer = io.BytesIO()
            stream = codecs.getwriter(CODEC_NAME)(buffer)
            stream.write(obj)
            stream.flush()
            return buffer.getvalue()

        return self.idnatests.test_encode(encode=encode)

    def testIncrementalDecoder(self):
        # Tests derived from Python standard library test/test_codecs.py

        incremental_tests = (
            ("python.org", b"python.org"),
            ("python.org.", b"python.org."),
            ("pyth\xf6n.org", b"xn--pythn-mua.org"),
            ("pyth\xf6n.org.", b"xn--pythn-mua.org."),
        )

        for decoded, encoded in incremental_tests:
            self.assertEqual(
                "".join(codecs.iterdecode((bytes([c]) for c in encoded), CODEC_NAME)),
                decoded,
            )

        decoder = codecs.getincrementaldecoder(CODEC_NAME)()
        self.assertEqual(
            decoder.decode(
                b"xn--xam",
            ),
            "",
        )
        self.assertEqual(
            decoder.decode(
                b"ple-9ta.o",
            ),
            "\xe4xample.",
        )
        self.assertEqual(decoder.decode(b"rg"), "")
        self.assertEqual(decoder.decode(b"", True), "org")

        decoder.reset()
        self.assertEqual(
            decoder.decode(
                b"xn--xam",
            ),
            "",
        )
        self.assertEqual(
            decoder.decode(
                b"ple-9ta.o",
            ),
            "\xe4xample.",
        )
        self.assertEqual(decoder.decode(b"rg."), "org.")
        self.assertEqual(decoder.decode(b"", True), "")

    def testIncrementalEncoder(self):
        # Tests derived from Python standard library test/test_codecs.py

        incremental_tests = (
            ("python.org", b"python.org"),
            ("python.org.", b"python.org."),
            ("pyth\xf6n.org", b"xn--pythn-mua.org"),
            ("pyth\xf6n.org.", b"xn--pythn-mua.org."),
        )
        for decoded, encoded in incremental_tests:
            self.assertEqual(b"".join(codecs.iterencode(decoded, CODEC_NAME)), encoded)

        encoder = codecs.getincrementalencoder(CODEC_NAME)()
        self.assertEqual(encoder.encode("\xe4x"), b"")
        self.assertEqual(encoder.encode("ample.org"), b"xn--xample-9ta.")
        self.assertEqual(encoder.encode("", True), b"org")

        encoder.reset()
        self.assertEqual(encoder.encode("\xe4x"), b"")
        self.assertEqual(encoder.encode("ample.org."), b"xn--xample-9ta.org.")
        self.assertEqual(encoder.encode("", True), b"")


if __name__ == "__main__":
    unittest.main()
