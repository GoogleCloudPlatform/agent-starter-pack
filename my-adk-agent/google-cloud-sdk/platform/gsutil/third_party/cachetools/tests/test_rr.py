import random
import unittest

from cachetools import RRCache

from . import CacheTestMixin


class RRCacheTest(unittest.TestCase, CacheTestMixin):
    Cache = RRCache

    def test_rr(self):
        cache = RRCache(maxsize=2, choice=min)
        self.assertEqual(min, cache.choice)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])
        self.assertNotIn(1, cache)

        cache[0] = 0
        self.assertEqual(2, len(cache))
        self.assertEqual(0, cache[0])
        self.assertEqual(3, cache[3])
        self.assertNotIn(2, cache)

        cache[4] = 4
        self.assertEqual(2, len(cache))
        self.assertEqual(3, cache[3])
        self.assertEqual(4, cache[4])
        self.assertNotIn(0, cache)

    def test_rr_getsizeof(self):
        cache = RRCache(maxsize=3, choice=min, getsizeof=lambda x: x)

        cache[1] = 1
        cache[2] = 2

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[1], 1)
        self.assertEqual(cache[2], 2)

        cache[3] = 3

        self.assertEqual(len(cache), 1)
        self.assertEqual(cache[3], 3)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)

        with self.assertRaises(ValueError):
            cache[4] = 4
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache[3], 3)

    def test_rr_update_existing(self):
        cache = RRCache(maxsize=2, choice=min)

        cache[1] = 1
        cache[2] = 2
        cache[1] = "updated"
        cache[3] = 3

        self.assertIn(2, cache)
        self.assertIn(3, cache)
        self.assertNotIn(1, cache)

    def test_rr_bad_choice(self):
        def bad_choice(seq):
            raise ValueError("test error")

        cache = RRCache(maxsize=2, choice=bad_choice)
        cache[1] = 1
        cache[2] = 2
        with self.assertRaises(ValueError):
            cache[3] = 3

    def test_rr_default_choice(self):
        cache = RRCache(maxsize=2)
        self.assertIs(cache.choice, random.choice)
