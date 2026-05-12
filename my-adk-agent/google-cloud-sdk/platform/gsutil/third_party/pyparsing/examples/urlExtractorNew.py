# URL extractor
# Copyright 2004, Paul McGuire
from collections import Counter
import pprint
from urllib.request import urlopen

from pyparsing import makeHTMLTags, pyparsing_common as ppc, FollowedBy, trace_parse_action

# Define the pyparsing grammar for a URL, that is:
#    URLlink ::= <a href= URL>linkText</a>
#    URL ::= doubleQuotedString | alphanumericWordPath
# Note that whitespace may appear just about anywhere in the link.  Note also
# that it is not necessary to explicitly show this in the pyparsing grammar; by default,
# pyparsing skips over whitespace between tokens.
linkOpenTag, linkCloseTag = makeHTMLTags("a")
link = linkOpenTag + linkOpenTag.tag_body("body") + linkCloseTag.suppress()


# Add a parse action to expand relative URLs
def expand_relative_url(t):
    url = t.href
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith(("/", "?", "#")):
        url = "https://www.cnn.com" + url

    # Put modified URL back into input tokens
    t["href"] = url


link.add_parse_action(expand_relative_url)

# Go get some HTML with some links in it.
with urlopen("https://www.cnn.com/") as serverListPage:
    htmlText = serverListPage.read().decode()

# scanString is a generator that loops through the input htmlText, and for each
# match yields the tokens and start and end locations (for this application, we are
# not interested in the start and end values).
for toks, strt, end in link.scanString(htmlText):
    print(toks.startA.href, "->", toks.body)

# Create dictionary with a dict comprehension, assembled from each pair of tokens returned
# from a matched URL.
links = {toks.body: toks.href for toks, _, _ in link.scanString(htmlText)}
pprint.pprint(links)

# Parse the urls in the links using pyparsing_common.url, and tally up all
# the different domains in a Counter.
domains = Counter()
for url in links.values():

    print(url)
    parsed = ppc.url.parseString(url)

    # print parsed fields for each new url
    if parsed.host not in domains:
        print(parsed.dump())
        print()

    # update domain counter
    domains[parsed.host] += 1


# Print out a little table of all the domains in the urls
max_domain_len = max(len(d) for d in domains)
print()
print("{:{}s}  {}".format("Domain", max_domain_len, "Count"))
print("{:=<{}}  {:=<5}".format("", max_domain_len, ""))

for domain, count in domains.most_common():
    print("{:{}s}  {:5d}".format(domain, max_domain_len, count))
