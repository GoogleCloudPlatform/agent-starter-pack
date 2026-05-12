# BUILDING

pyparsing uses the [flit](https://flit.readthedocs.io/) build system
that is compliant with [PEP 517](https://www.python.org/dev/peps/pep-0517/).
Therefore, any PEP 517-compliant tools can be used to build it.


## Building using flit

To build the distribution files using flit, type:

```
$ flit build
```

The generated sdist and wheel will be placed in `dist/` directory.


## Building using build

[build](https://github.com/pypa/build) is a generic builder for PEP 517
projects.  To build the distribution files using build, type:

```
$ pyproject-build
```

The generated sdist and wheel will be placed in `dist/` directory.


## Testing

pyparsing uses [tox](https://tox.wiki/en/latest/) to run tests.
In order to run the complete test suite, type:

```
$ tox
```
