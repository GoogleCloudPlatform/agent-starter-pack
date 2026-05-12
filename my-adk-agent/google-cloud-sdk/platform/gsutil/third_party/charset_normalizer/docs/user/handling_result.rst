================
 Handling Result
================

When initiating search upon a buffer, bytes or file you can assign the return value and fully exploit it.

 ::

    my_byte_str = 'Bсеки човек има право на образование.'.encode('cp1251')

    # Assign return value so we can fully exploit result
    result = from_bytes(
        my_byte_str
    ).best()

    print(result.encoding)  # cp1251

Using CharsetMatch
----------------------------

Here, ``result`` is a ``CharsetMatch`` object or ``None``.

.. autoclass:: charset_normalizer.CharsetMatch
    :members:

