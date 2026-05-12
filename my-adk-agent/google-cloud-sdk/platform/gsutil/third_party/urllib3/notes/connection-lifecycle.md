# Connection lifecycle

## Current implementation

`HTTPConnection` should be instantiated with `host` and `port` of the
**first origin being connected to** to reach the target origin. This either means
the target origin itself or the proxy origin if one is desired.

```python
import urllib3.connection

# Initialize the HTTPSConnection ('https://...')
conn = urllib3.connection.HTTPSConnection(
    host="example.com",
    # Here you can configure other options like
    # 'ssl_minimum_version', 'ca_certs', etc.
)

# Set the connect timeout either in the
# constructor above or via the property.
conn.timeout = 3.0  # (connect timeout)
```

If using CONNECT tunneling with the proxy, call `HTTPConnection.set_tunnel()`
with the tunneled host, port, and headers. This should be called before calling
`HTTPConnection.connect()` or sending a request.

```python
conn = urllib3.connection.HTTPConnection(
    # Remember that the *first* origin we want to connect to should
    # be configured as 'host' and 'port', *not* the target origin.
    host="myproxy.net",
    port=8080,
    proxy="http://myproxy.net:8080"
)

conn.set_tunnel("example.com", scheme="http", headers={"Proxy-Header": "value"})
```

Connect to the first origin by calling the `HTTPConnection.connect()` method.
If an error occurs here you can check whether the error occurred during the
connection to the proxy if `HTTPConnection.has_connected_to_proxy` is false.
If the value is true then the error didn't occur while connecting to a proxy.

```python
# Explicitly connect to the origin. This isn't
# required as sending the first request will
# automatically connect if not done explicitly.
conn.connect()
```

After connecting to the origin, the connection can be checked to see if `is_verified` is set to true. If not the `HTTPConnectionPool` would emit a warning. The warning only matters for when verification is disabled, because otherwise an error is raised on unverified TLS handshake.

```python
if not conn.is_verified:
    # There isn't a verified TLS connection to target origin.
if not conn.proxy_is_verified:
    # There isn't a verified TLS connection to proxy origin.
```

If the read timeout is different from the connect timeout then the
`HTTPConnection.timeout` property can be changed at this point.

```python
conn.timeout = 5.0  # (read timeout)
```

Then the HTTP request can be sent with `HTTPConnection.request()`. If a `BrokenPipeError` is raised while sending the request body it can be swallowed as a response can still be received from the origin even when the request isn't completely sent.

```python
try:
    conn.request("GET", "/")
except BrokenPipeError:
    # We can still try to get a response!

resp = conn.getresponse()
```

Then response headers (and other info) are read from the connection via `HTTPConnection.getresponse()` and returned as a `urllib3.HTTPResponse`. The `HTTPResponse` instance carries a reference to the `HTTPConnection` instance so the connection can be closed if the connection gets into an undefined protocol state.

```python
assert resp.connection is conn
```

If pooling is in use the `HTTPConnectionPool` will set `_pool` on the `HTTPResponse` instance. This will return the connection to the pool once the response is exhausted. If retries are in use set `retries` on the `HTTPResponse` instance.

```python
# Set by the HTTPConnectionPool before returning to the caller.
resp = conn.getresponse()
resp._pool = pool

# This will call resp._pool._put_conn(resp.connection)
# Connection can get auto-released by exhausting.
resp.release_conn()
```

If any error is received from connecting to the origin, sending the request, or receiving the response, the caller will call `HTTPConnection.close()` and discard the connection. Connections can be re-used after being closed, a new TCP connection to proxies and origins will be established.

If instead of a tunneling proxy we were using a forwarding proxy then we configure the `HTTPConnection` similarly, except instead of `set_tunnel()` we send absolute URLs to `HTTPConnection.request()`:

```python
import urllib3.connection

# Initialize the HTTPConnection.
conn = urllib3.connection.HTTPConnection(
    host="myproxy.net",
    port=8080,
    proxy="http://myproxy.net:8080"
)

# You can request HTTP or HTTPS resources over the proxy
# using the absolute URL.
conn.request("GET", "http://example.com")
resp = conn.getresponse()

conn.request("GET", "https://example.com")
resp = conn.getresponse()
```

### HTTP/HTTPS/proxies

This is how `HTTPConnection` instances will be configured and used when a `PoolManager` or `ProxyManager` receives a given config:

- No proxy, HTTP origin -> `HTTPConnection`
- No proxy, HTTPS origin -> `HTTPSConnection`
- HTTP proxy, HTTP origin -> `HTTPConnection` in forwarding mode
- HTTP proxy, HTTPS origin -> `HTTPSConnection` in tunnel mode
- HTTPS proxy, HTTP origin -> `HTTPSConnection` in forwarding mode
- HTTPS proxy, HTTPS origin -> `HTTPSConnection` in tunnel mode
- HTTPS proxy, HTTPS origin, `ProxyConfig.use_forwarding_for_https=True` -> `HTTPSConnection` in forwarding mode
