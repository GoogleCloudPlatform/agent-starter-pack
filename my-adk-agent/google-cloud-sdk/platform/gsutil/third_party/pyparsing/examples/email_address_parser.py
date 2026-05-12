#
# email_address_parser.py
#
# email address parser based on RFC 5322 BNF segments
# - see https://datatracker.ietf.org/doc/html/rfc5322#section-3.4.
#
# The returned parse results include named fields 'account' and 'domain'
# for emails of the form `account@domain`.
#
# Copyright 2024, by Paul McGuire
#
from pyparsing import Regex

email_address = Regex(
    # RFC5322 email address
    r"""(?P<account>(?:(?:\"[\w\s()<>[\].,;:@"]+\")|[!#-'*+\-/-9=?A-Z\^-~.]+))"""
    "@"
    r"""(?P<domain>(?:(?:(?!-)[!#-'*+\-/-9=?A-Z\^-~]{1,63}(?<!-)\.)+[A-Za-z0-9]{2,6})|(?:\[[!-Z^-~]+\]))(?:\b|$)"""
).set_name("email address")


def main():
    success, _ = email_address.run_tests(
        """\
        email@example.com
        firstname.lastname@example.com
        email@subdomain.example.com
        firstname+lastname@example.com
        email@123.123.123.123
        email@[123.123.123.123]
        "email"@example.com
        1234567890@example.com
        email@example-one.com
        _______@example.com
        email@example.name
        email@example.museum
        email@example.co.jp
        firstname-lastname@example.com
        """
    )

    assert success


if __name__ == "__main__":
    main()
