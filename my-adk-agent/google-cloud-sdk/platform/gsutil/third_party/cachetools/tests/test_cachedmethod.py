import unittest
import warnings


from cachetools import LRUCache, cachedmethod, keys


class Cached:

    class_cache = LRUCache(2)
    class_count = 0

    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

    @cachedmethod(lambda self: self.cache)
    def get(self, value):
        self.count += 1
        return self.count

    @cachedmethod(lambda self: self.cache, key=keys.typedmethodkey)
    def get_typedmethod(self, value):
        self.count += 1
        return self.count

    @classmethod
    @cachedmethod(lambda cls: cls.class_cache)
    def get_classmethod(cls, value):
        cls.class_count += 1
        return cls.class_count

    @classmethod
    @cachedmethod(lambda cls: cls.class_cache, key=keys.typedmethodkey)
    def get_typedclassmethod(cls, value):
        cls.class_count += 1
        return cls.class_count


class Locked:
    def __init__(self, cache):
        self.cache = cache
        self.count = 0
        self.lock_count = 0

    @cachedmethod(lambda self: self.cache, lock=lambda self: self)
    def get(self, value):
        self.count += 1
        return self.count

    def __enter__(self):
        self.lock_count += 1

    def __exit__(self, *exc):
        pass


class Conditioned(Locked):
    def __init__(self, cache):
        Locked.__init__(self, cache)
        self.wait_count = 0
        self.notify_count = 0

    @cachedmethod(lambda self: self.cache, condition=lambda self: self)
    def get(self, value):
        return Locked.get.__wrapped__(self, value)

    @cachedmethod(
        lambda self: self.cache, lock=lambda self: self, condition=lambda self: self
    )
    def get_lock(self, value):
        return Locked.get.__wrapped__(self, value)

    def wait_for(self, predicate):
        self.wait_count += 1

    def notify_all(self):
        self.notify_count += 1


class Unhashable:
    def __init__(self, cache):
        self.cache = cache

    @cachedmethod(lambda self: self.cache)
    def get_default(self, value):
        return value

    @cachedmethod(lambda self: self.cache, key=keys.hashkey)
    def get_hashkey(self, value):
        return value

    # https://github.com/tkem/cachetools/issues/107
    def __hash__(self):
        raise TypeError("unhashable type")


class CachedMethodTest(unittest.TestCase):
    def test_dict(self):
        cached = Cached({})

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.get(1.0), 2)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 3)

    def test_typedmethod_dict(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get_typedmethod(0), 1)
        self.assertEqual(cached.get_typedmethod(1), 2)
        self.assertEqual(cached.get_typedmethod(1), 2)
        self.assertEqual(cached.get_typedmethod(1.0), 3)
        self.assertEqual(cached.get_typedmethod(1.0), 3)
        self.assertEqual(cached.get_typedmethod(0.0), 4)
        self.assertEqual(cached.get_typedmethod(0), 5)

    def test_lru(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.get(1.0), 2)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 3)

    def test_typedmethod_lru(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get_typedmethod(0), 1)
        self.assertEqual(cached.get_typedmethod(1), 2)
        self.assertEqual(cached.get_typedmethod(1), 2)
        self.assertEqual(cached.get_typedmethod(1.0), 3)
        self.assertEqual(cached.get_typedmethod(1.0), 3)
        self.assertEqual(cached.get_typedmethod(0.0), 4)
        self.assertEqual(cached.get_typedmethod(0), 5)

    def test_nospace(self):
        cached = Cached(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.get(1.0), 4)
        self.assertEqual(cached.get(1.0), 5)

    def test_nocache(self):
        cached = Cached(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.assertEqual(cached.get(0), 1)
            self.assertEqual(cached.get(1), 2)
            self.assertEqual(cached.get(1), 3)
            self.assertEqual(cached.get(1.0), 4)
            self.assertEqual(cached.get(1.0), 5)

        self.assertEqual(len(w), 5)
        self.assertIs(w[0].category, DeprecationWarning)

    def test_weakref(self):
        import weakref
        import fractions
        import gc

        # in Python 3.7, `int` does not support weak references even
        # when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):
                return Int(fractions.Fraction.__add__(self, other))

        cached = Cached(weakref.WeakValueDictionary(), count=Int(0))

        self.assertEqual(cached.get(0), 1)
        gc.collect()
        self.assertEqual(cached.get(0), 1)

        ref = cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)

        ref = cached.get_typedmethod(2)
        self.assertEqual(ref, 3)
        self.assertEqual(cached.get_typedmethod(1), 4)
        self.assertEqual(cached.get_typedmethod(1.0), 5)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 6)

    def test_locked_dict(self):
        cached = Locked({})

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.lock_count, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock_count, 4)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock_count, 5)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.lock_count, 6)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.lock_count, 7)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.lock_count, 9)

    def test_locked_nospace(self):
        cached = Locked(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.lock_count, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock_count, 4)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.lock_count, 6)
        self.assertEqual(cached.get(1.0), 4)
        self.assertEqual(cached.lock_count, 8)
        self.assertEqual(cached.get(1.0), 5)
        self.assertEqual(cached.lock_count, 10)

    def test_locked_nocache(self):
        cached = Locked(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.assertEqual(cached.get(0), 1)
            self.assertEqual(cached.get(1), 2)
            self.assertEqual(cached.get(1), 3)
            self.assertEqual(cached.get(1.0), 4)
            self.assertEqual(cached.get(1.0), 5)
            self.assertEqual(cached.lock_count, 0)

        self.assertEqual(len(w), 5)
        self.assertIs(w[0].category, DeprecationWarning)

    def test_condition_dict(self):
        cached = Conditioned({})

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.lock_count, 3)
        self.assertEqual(cached.wait_count, 1)
        self.assertEqual(cached.notify_count, 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock_count, 6)
        self.assertEqual(cached.wait_count, 2)
        self.assertEqual(cached.notify_count, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock_count, 7)
        self.assertEqual(cached.wait_count, 3)
        self.assertEqual(cached.notify_count, 2)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.lock_count, 8)
        self.assertEqual(cached.wait_count, 4)
        self.assertEqual(cached.notify_count, 2)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.lock_count, 9)
        self.assertEqual(cached.wait_count, 5)
        self.assertEqual(cached.notify_count, 2)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.lock_count, 12)
        self.assertEqual(cached.wait_count, 6)
        self.assertEqual(cached.notify_count, 3)

    def test_condition_nospace(self):
        cached = Conditioned(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.lock_count, 3)
        self.assertEqual(cached.wait_count, 1)
        self.assertEqual(cached.notify_count, 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock_count, 6)
        self.assertEqual(cached.wait_count, 2)
        self.assertEqual(cached.notify_count, 2)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.lock_count, 9)
        self.assertEqual(cached.wait_count, 3)
        self.assertEqual(cached.notify_count, 3)
        self.assertEqual(cached.get(1.0), 4)
        self.assertEqual(cached.lock_count, 12)
        self.assertEqual(cached.wait_count, 4)
        self.assertEqual(cached.notify_count, 4)
        self.assertEqual(cached.get(1.0), 5)
        self.assertEqual(cached.lock_count, 15)
        self.assertEqual(cached.wait_count, 5)
        self.assertEqual(cached.notify_count, 5)

    def test_condition_nocache(self):
        cached = Conditioned(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.assertEqual(cached.get(0), 1)
            self.assertEqual(cached.get(1), 2)
            self.assertEqual(cached.get(1), 3)
            self.assertEqual(cached.get(1.0), 4)
            self.assertEqual(cached.get(1.0), 5)
            self.assertEqual(cached.lock_count, 0)
            self.assertEqual(cached.wait_count, 0)
            self.assertEqual(cached.notify_count, 0)

        self.assertEqual(len(w), 5)
        self.assertIs(w[0].category, DeprecationWarning)

    def test_unhashable(self):
        cached = Unhashable(LRUCache(maxsize=0))

        self.assertEqual(cached.get_default(0), 0)
        self.assertEqual(cached.get_default(1), 1)

        with self.assertRaises(TypeError):
            cached.get_hashkey(0)

    def test_wrapped(self):
        cache = {}
        cached = Cached(cache)

        self.assertEqual(len(cache), 0)
        self.assertEqual(Cached.get.__wrapped__(cached, 0), 1)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.get(0), 2)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.get(0), 2)
        self.assertEqual(len(cache), 1)

    def test_attributes(self):
        cache = {}
        cached = Cached(cache)

        self.assertIs(Cached.get.cache(cached), cache)
        self.assertIs(Cached.get.cache_key, keys.methodkey)
        self.assertIs(Cached.get.cache_lock, None)
        self.assertIs(Cached.get.cache_condition, None)

    def test_attributes_lock(self):
        cache = {}
        cached = Locked(cache)

        self.assertIs(Locked.get.cache(cached), cache)
        self.assertIs(Locked.get.cache_key, keys.methodkey)
        self.assertIs(Locked.get.cache_lock(cached), cached)
        self.assertIs(Locked.get.cache_condition, None)

    def test_attributes_cond(self):
        cache = {}
        cached = Conditioned(cache)

        self.assertIs(Conditioned.get.cache(cached), cache)
        self.assertIs(Conditioned.get.cache_key, keys.methodkey)
        self.assertIs(Conditioned.get.cache_lock(cached), cached)
        self.assertIs(Conditioned.get.cache_condition(cached), cached)

    def test_clear(self):
        cache = {}
        cached = Cached(cache)

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        Cached.get.cache_clear(cached)
        self.assertEqual(len(cache), 0)

    def test_clear_locked(self):
        cache = {}
        cached = Locked(cache)

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.lock_count, 2)
        Locked.get.cache_clear(cached)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.lock_count, 3)

    def test_clear_condition(self):
        cache = {}
        cached = Conditioned(cache)

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.lock_count, 3)
        Conditioned.get.cache_clear(cached)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.lock_count, 4)


class CachedClassMethodTest(unittest.TestCase):

    def test(self):
        Cached.class_cache = LRUCache(2)
        Cached.class_count = 0
        cached = Cached(None)

        self.assertEqual(cached.get_classmethod(0), 1)
        self.assertEqual(Cached.get_classmethod(0), 1)
        self.assertEqual(cached.get_classmethod(1), 2)
        self.assertEqual(Cached.get_classmethod(1), 2)
        self.assertEqual(cached.get_classmethod(1), 2)
        self.assertEqual(Cached.get_classmethod(1), 2)
        self.assertEqual(cached.get_classmethod(1.0), 2)
        self.assertEqual(Cached.get_classmethod(1.0), 2)
        self.assertEqual(Cached.get_classmethod(1.1), 3)
        self.assertEqual(cached.get_classmethod(1.1), 3)

        cached.class_cache.clear()
        self.assertEqual(cached.get_classmethod(1), 4)

    def test_typedmethod(self):
        Cached.class_cache = LRUCache(2)
        Cached.class_count = 0
        cached = Cached(None)

        self.assertEqual(cached.get_typedclassmethod(0), 1)
        self.assertEqual(Cached.get_typedclassmethod(0), 1)
        self.assertEqual(cached.get_typedclassmethod(1), 2)
        self.assertEqual(Cached.get_typedclassmethod(1), 2)
        self.assertEqual(cached.get_typedclassmethod(1.0), 3)
        self.assertEqual(Cached.get_typedclassmethod(1.0), 3)
        self.assertEqual(cached.get_typedclassmethod(0.0), 4)
        self.assertEqual(Cached.get_typedclassmethod(0.0), 4)
        self.assertEqual(Cached.get_typedclassmethod(0), 5)
        self.assertEqual(cached.get_typedclassmethod(0), 5)
