#
# html_stripper.py
#
#  Sample code for stripping HTML markup tags and scripts from
#  HTML source files.
#
# Copyright (c) 2006, 2016, 2023, Paul McGuire
#
from urllib.request import urlopen
from pyparsing import (
    LineEnd,
    quoted_string,
    make_html_tags,
    common_html_entity,
    replace_html_entity,
    html_comment,
    any_open_tag,
    any_close_tag,
    replace_with,
)

# if <script> tags found, remove script content also
script_open, script_close = make_html_tags("script")
script_body = script_open + ... + script_close

# translate HTML entities
common_html_entity.set_parse_action(replace_html_entity)

stripper = (
        # parse quoted strings first, if they enclose HTML tags - keep these
        quoted_string
        # parse and translate HTML entities (&amp;, &lt;, &gt;, etc.)
        | common_html_entity
        # expressions to be stripped - suppress() will remove them when transforming
        | (
            html_comment | script_body | any_open_tag | any_close_tag
          ).suppress()
)

repeated_newlines = LineEnd()[2, ...]
repeated_newlines.set_parse_action(replace_with("\n\n"))


if __name__ == '__main__':
    # get some HTML
    target_url = "https://wiki.python.org/moin/PythonDecoratorLibrary"
    with urlopen(target_url) as targetPage:
        target_html = targetPage.read().decode("UTF-8")

    # first pass, strip out tags and translate entities
    # (use transform_string() instead of parse_string - will do
    # suppressions and parse actions)
    first_pass = stripper.transform_string(target_html)

    # first pass leaves many blank lines, collapse these down
    second_pass = repeated_newlines.transform_string(first_pass)

    print(second_pass)
