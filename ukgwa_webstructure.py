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
        self.ukgwa_prefix = "https://webarchive.nationalarchives.gov.uk/"
        self.fields['SCHEME'] = 0
        self.fields['NETLOC'] = 1
        self.fields['PATH'] = 2
        self.fields['FILE'] = 3
        self.fields['QUERY'] = 4
        self.fields['TREE'] = 5
        self.fields['URL'] = 6

    def add_entry(self, url, identifier = None):

        if identifier is None:
            identifier = url
        parsed = self._parseurl(url)
        if "." in parsed.path.split("/")[-1]:
            file_name = parsed.path.split("/")[-1]
            path = parsed.path[:-len(file_name)]
        else:
            file_name = ""
            path = parsed.path
        super().add_entry(identifier, [parsed.scheme, parsed.netloc, path, file_name, parsed.query, self._domaintotree(parsed.netloc, path, True), url])

    def get_url_tree(self, identifier, path=True):
        tree = self.get_field(identifier, 'TREE')
        if path:
            return tree
        else:
            first_dollar = tree.index('$')
            if first_dollar > 0:  #something wrong if it is 0!
                return tree[:first_dollar+1]
            else:
                return tree

    def _parseurl(self, url):

        if url[:len(self.ukgwa_prefix)] == self.ukgwa_prefix:
            url = url[len(self.ukgwa_prefix) + 15:]
        if url[:4] != "http":
            url = "https://" + url
        parsed = urlparse(url)
        return parsed

    def _domaintotree(self, domain, path = "", strip_www = False):

        if strip_www:
            if domain[:4] == "www.":
                domain = domain[4:]
        tree = domain.split(".")
        tree = [r for r in reversed(tree)] + ['$']
        tree += [p for p in path.split("/") if len(p) > 0]
        return tree


if __name__ == "__main__":
    struc = UKGWAStructure()
    parsed = struc._parseurl("https://webarchive.nationalarchives.gov.uk/20100101000000/http://www.gov.uk/guidance")
    print(parsed)
    parsed = struc._parseurl("http://www.gov.uk/guidance/index.html")
    print(parsed)
    struc.add_entry("http://www.gov.uk/guidance/index.html",1)
    struc.add_entry("http://www.gov.uk",2)
    struc.add_entry("http://www.gov.uk/guidance",3)
    struc.add_entry("www.gov.uk",4)
    print(struc.get_field(1, "URL"))
    print(struc.get_field(2, "URL"))
    print(struc.get_field(3, "URL"))
    print(struc.get_field(4, "URL"))
    #print(struc.get_entry_url(1))
    #print(struc.get_entry_url(2))
    #print(struc.get_entry_url(3))
    #print(struc.get_entry_url(4))
    print(struc.comparison(2,'TREE','isprefix', struc.get_field(1,'TREE')))
    print(struc.get_url_tree(1,True))
    print(struc.get_url_tree(1,False))
    exit()
    print(struc.domaintotree(parsed.netloc))
    print(struc.domaintotree(parsed.netloc, strip_www = True))
    print(struc.domaintotree(parsed.netloc, path = parsed.path, strip_www = True))
    struc.add_entry("www.gov.uk", 5)
    print(struc.index)
    struc.add_entry("www.gov.uk")
    print(struc.index)

