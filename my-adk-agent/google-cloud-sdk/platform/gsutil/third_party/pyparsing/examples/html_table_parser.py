#
# htmlTableParser.py
#
# Example of parsing a simple HTML table into a list of rows, and optionally into a little database
#
# Copyright 2019, Paul McGuire
#

import pyparsing as pp
import urllib.request


# define basic HTML tags, and compose into a Table
table, table_end = pp.make_html_tags("table")
thead, thead_end = pp.make_html_tags("thead")
tbody, tbody_end = pp.make_html_tags("tbody")
tr, tr_end = pp.make_html_tags("tr")
th, th_end = pp.make_html_tags("th")
td, td_end = pp.make_html_tags("td")
a, a_end = pp.make_html_tags("a")

# method to strip HTML tags from a string - will be used to clean up content of table cells
strip_html = (pp.any_open_tag | pp.any_close_tag).suppress().transform_string

# expression for parsing <a href="url">text</a> links, returning a (text, url) tuple
link = pp.Group(a + a.tag_body("text") + a_end.suppress())


def extract_text_and_url(t):
    return (t[0].text, t[0].href)


link.addParseAction(extract_text_and_url)


# method to create table rows of header and data tags
def table_row(start_tag, end_tag):
    body = start_tag.tag_body
    body.add_parse_action(pp.token_map(str.strip), pp.token_map(strip_html))
    row = pp.Group(
        tr.suppress()
        + (start_tag.suppress() + body + end_tag.suppress())[...]
        + tr_end.suppress()
    )
    return row


th_row = table_row(th, th_end)
td_row = table_row(td, td_end)

# define expression for overall table - may vary slightly for different pages
html_table = (
    table
    + tbody
    + th_row[...]("headers")
    + td_row[...]("rows")
    + tbody_end
    + table_end
)


# read in a web page containing an interesting HTML table
with urllib.request.urlopen(
    "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
) as page:
    page_html = page.read().decode()

tz_table = html_table.searchString(page_html)[0]

# convert rows to dicts
rows = [dict(zip(tz_table.headers[0], row)) for row in tz_table.rows]

# make a dict keyed by TZ database identifier
# (get identifier key from second column header)
identifier_key = tz_table.headers[0][1]
tz_db = {row[identifier_key]: row for row in rows}

from pprint import pprint

pprint(tz_db["America/Chicago"])
pprint(tz_db["Zulu"])
