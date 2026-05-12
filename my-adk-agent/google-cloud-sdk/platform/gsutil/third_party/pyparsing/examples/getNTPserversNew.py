# getNTPserversNew.py
#
# Demonstration of the parsing module, implementing a HTML page scanner,
# to extract a list of NTP time servers from the NIST web site.
#
# Copyright 2004-2010, by Paul McGuire
# September, 2010 - updated to more current use of setResultsName, new NIST URL
#
import pyparsing as pp

ppc = pp.pyparsing_common
from urllib.request import urlopen

integer = pp.Word(pp.nums)
ipAddress = ppc.ipv4_address()
hostname = pp.DelimitedList(pp.Word(pp.alphas, pp.alphanums + "-_"), ".", combine=True)
tdStart, tdEnd = pp.make_html_tags("td")
timeServerPattern = (
    tdStart
    + hostname("hostname")
    + tdEnd
    + tdStart
    + ipAddress("ipAddr")
    + tdEnd
    + tdStart
    + tdStart.tag_body("loc")
    + tdEnd
)

# get list of time servers
nistTimeServerURL = "https://tf.nist.gov/tf-cgi/servers.cgi#"
with urlopen(nistTimeServerURL) as serverListPage:
    serverListHTML = serverListPage.read().decode("UTF-8")

addrs = {}
for srvr, startloc, endloc in timeServerPattern.scan_string(serverListHTML):
    print(f"{srvr.ipAddr} ({srvr.hostname.strip()}) - {srvr.loc.strip()}")
    addrs[srvr.ipAddr] = srvr.loc
