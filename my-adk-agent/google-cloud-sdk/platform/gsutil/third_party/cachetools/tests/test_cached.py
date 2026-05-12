import unittest
import warnings

import cachetools
import cachetools.keys


class CountedLock:
    def __init__(self):
        self.count = 0

    def __enter__(self):
        self.count += 1

    def __exit__(self, *exc):
        pass


class CountedCondition(CountedLock):
    def __init__(self):
        CountedLock.__init__(self)
        self.wait_count = 0
        self.notify_count = 0

    def wait_for(self, predicate):
        self.wait_count += 1

    def notify_all(self):
        self.notify_count += 1


class DecoratorTestMixin:
    def cache(self, minsize):
        raise NotImplementedError

    def func(self, *args, **kwargs):
        if hasattr(self, "count"):
            self.count += 1
        else:
            self.count = 0
        return self.count

    def test_decorator(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertNotIn(cachetools.keys.hashkey(1), cache)
        self.assertNotIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertIn(cachetools.keys.hashkey(1), cache)
        self.assertIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 1)
        self.assertEqual(len(cache), 2)

    def test_decorator_typed(self):
        cache = self.cache(3)
        key = cachetools.keys.typedkey
        wrapper = cachetools.cached(cache, key=key)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertNotIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 2)
        self.assertEqual(len(cache), 3)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(wrapper(1.0), 2)
        self.assertEqual(len(cache), 3)

    def test_decorator_lock(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 2)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 5)

    def test_decorator_condition(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 3)
        self.assertEqual(cond.wait_count, 1)
        self.assertEqual(cond.notify_count, 1)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 6)
        self.assertEqual(cond.wait_count, 2)
        self.assertEqual(cond.notify_count, 2)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 7)
        self.assertEqual(cond.wait_count, 3)
        self.assertEqual(cond.notify_count, 2)

    def test_decorator_lock_condition(self):
        cache = self.cache(2)
        lock = CountedLock()
        cond = CountedCondition()
        wrapper = cachetools.cached(cache, lock=lock, condition=cond)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 3)
        self.assertEqual(cond.wait_count, 1)
        self.assertEqual(cond.notify_count, 1)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 6)
        self.assertEqual(cond.wait_count, 2)
        self.assertEqual(cond.notify_count, 2)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 7)
        self.assertEqual(cond.wait_count, 3)
        self.assertEqual(cond.notify_count, 2)

    def test_decorator_wrapped(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertEqual(wrapper.__wrapped__, self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(wrapper(0), 1)
        self.assertEqual(len(cache), 1)

    def test_decorator_attributes(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertIs(wrapper.cache, cache)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertIs(wrapper.cache_lock, None)
        self.assertIs(wrapper.cache_condition, None)

    def test_decorator_attributes_lock(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)

        self.assertIs(wrapper.cache, cache)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertIs(wrapper.cache_lock, lock)
        self.assertIs(wrapper.cache_condition, None)

    def test_decorator_attributes_condition(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.func)

        self.assertIs(wrapper.cache, cache)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertIs(wrapper.cache_lock, lock)
        self.assertIs(wrapper.cache_condition, cond)

    def test_decorator_clear(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)

    def test_decorator_clear_lock(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertEqual(lock.count, 2)
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 3)

    def test_decorator_clear_condition(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.func)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertEqual(lock.count, 3)
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 4)


class CacheWrapperTest(unittest.TestCase, DecoratorTestMixin):
    def cache(self, minsize):
        return cachetools.Cache(maxsize=minsize)

    def test_decorator_info(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))

    def test_decorator_lock_info(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 3)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 6)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(lock.count, 7)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 8)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        self.assertEqual(lock.count, 9)
        wrapper.cache_clear()
        self.assertEqual(lock.count, 10)
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 11)

    def test_decorator_lock_info_deprecated(self):
        cache = self.cache(2)
        key = cachetools.keys.hashkey
        lock = CountedLock()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # passing `ìnfo` as positional parameter is deprecated
            wrapper = cachetools.cached(cache, key, lock, True)(self.func)
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))

    def test_decorator_condition_info(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(lock.count, 5)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 8)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(lock.count, 9)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 10)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        self.assertEqual(lock.count, 11)
        wrapper.cache_clear()
        self.assertEqual(lock.count, 12)
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 13)

    def test_decorator_lock_condition_info(self):
        cache = self.cache(2)
        lock = CountedLock()
        cond = CountedCondition()
        wrapper = cachetools.cached(cache, lock=lock, condition=cond, info=True)(
            self.func
        )
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(lock.count, 5)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 8)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(lock.count, 9)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 10)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        self.assertEqual(lock.count, 11)
        wrapper.cache_clear()
        self.assertEqual(lock.count, 12)
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 13)

    def test_zero_size_cache_decorator(self):
        cache = self.cache(0)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)

    def test_zero_size_cache_decorator_lock(self):
        cache = self.cache(0)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 2)

    def test_zero_size_cache_decorator_condition(self):
        cache = self.cache(0)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 3)

    def test_zero_size_cache_decorator_info(self):
        cache = self.cache(0)
        wrapper = cachetools.cached(cache, info=True)(self.func)

        self.assertEqual(wrapper.cache_info(), (0, 0, 0, 0))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, 0, 0))

    def test_zero_size_cache_decorator_lock_info(self):
        cache = self.cache(0)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock, info=True)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 0, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 3)
        self.assertEqual(wrapper.cache_info(), (0, 1, 0, 0))
        self.assertEqual(lock.count, 4)


class DictWrapperTest(unittest.TestCase, DecoratorTestMixin):
    def cache(self, minsize):
        return dict()

    def test_decorator_info(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, None, 1))
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, None, 2))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, None, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))


class NoneWrapperTest(unittest.TestCase):
    def func(self, *args, **kwargs):
        return args + tuple(kwargs.items())

    def test_decorator(self):
        wrapper = cachetools.cached(None)(self.func)

        self.assertEqual(wrapper(0), (0,))
        self.assertEqual(wrapper(1), (1,))
        self.assertEqual(wrapper(1, foo="bar"), (1, ("foo", "bar")))

    def test_decorator_attributes(self):
        wrapper = cachetools.cached(None)(self.func)

        self.assertIs(wrapper.cache, None)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertIs(wrapper.cache_lock, None)

    def test_decorator_clear(self):
        wrapper = cachetools.cached(None)(self.func)

        wrapper.cache_clear()  # no-op

    def test_decorator_info(self):
        wrapper = cachetools.cached(None, info=True)(self.func)

        self.assertEqual(wrapper.cache_info(), (0, 0, 0, 0))
        self.assertEqual(wrapper(0), (0,))
        self.assertEqual(wrapper.cache_info(), (0, 1, 0, 0))
        self.assertEqual(wrapper(1), (1,))
        self.assertEqual(wrapper.cache_info(), (0, 2, 0, 0))
        wrapper.cache_clear()
        self.assertEqual(wrapper.cache_info(), (0, 0, 0, 0))
