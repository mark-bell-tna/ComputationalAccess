#!/usr/bin/python3

from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import urlparse
import re
import sys
from ukgwa_view import UKGWAView

class UKGWAStructure(UKGWAView):

    def __init__(self):

        super().__init__()
        self.fields['SCHEME'] = 0
        self.fields['NETLOC'] = 1
        self.fields['PATH'] = 2
        self.fields['QUERY'] = 3

    def add_entry(self, url, identifier = None):

        if identifier is None:
            identifier = url
        parsed = self._parseurl(url)
        super().add_entry(self.index[identifier], [parsed.schem, parsed.netloc, parsed.path, parsed.query])

    def _parseurl(self, url):

        if url[:4] != "http":
            url = "https://" + url
        parsed = urlparse(url)
        return parsed

    def domaintotree(self, domain, path = "", strip_www = False):

        if strip_www:
            if domain[:4] == "www.":
                domain = domain[4:]
        tree = domain.split(".")
        tree = [r for r in reversed(tree)] + ['$']
        tree += [p for p in path.split("/") if len(p) > 0]
        return tree


if __name__ == "__main__":
    struc = UKGWAStructure()
    parsed = struc._parseurl("http://www.gov.uk/guidance")
    print(struc.domaintotree(parsed.netloc))
    print(struc.domaintotree(parsed.netloc, strip_www = True))
    print(struc.domaintotree(parsed.netloc, path = parsed.path, strip_www = True))
    exit()
    struc.add_entry("www.gov.uk", 5)
    print(struc.index)
    struc.add_entry("www.gov.uk")
    print(struc.index)

