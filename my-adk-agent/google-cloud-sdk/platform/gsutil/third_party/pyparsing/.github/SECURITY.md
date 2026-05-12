# Security Policy

Pyparsing itself has no known security vulnerabilities. It does not 
itself access any risk-inherent methods like `exec` or `eval`, nor does it import 
any modules not part of the Python standard library.

Parsers written with pyparsing *may* introduce security vulnerabilities. If so, this 
information should be forwarded to the maintainer of those parsers.

If you find that pyparsing itself has a security vulnerability, please report it to
https://tidelift.com/security.
