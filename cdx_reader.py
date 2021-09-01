#!/usr/bin/python3

import urllib.request
from urllib.error import HTTPError
from ukgwa_view import UKGWAView
from bs4 import BeautifulSoup
import re

class CDXReader(UKGWAView):

    def __init__(self, url):
        super().__init__()
        self.ukgwa_prefix = "https://webarchive.nationalarchives.gov.uk/ukgwa/"
        cdx_prefix = self.ukgwa_prefix + "-cdx?url="
        self.url = url
        self.cdx_url = cdx_prefix + url
        self.fields['SNAPSHOT'] = 0
        self.fields['MIME'] = 1
        self.fields['CODE'] = 2
        self.fields['CHECKSUM'] = 3
        self.fields['CHANGED'] = 4
        self.min_snapshot = 90000000000000
        self.max_snapshot = 00000000000000
        self.snapshot_count = 0
        self.snapshot_list = []
        try:
            self.return_list =  urllib.request.urlopen(self.cdx_url)
            self.success = True
        except:
            self.success = False
        if not self.success:
            self.return_list = self.backup()
            self.success = True

    def backup(self):

        url = self.ukgwa_prefix + "*/" + self.url
        version_list = []
        try:
            html = urllib.request.urlopen(url)
        except Exception as e:
            return
        soup = BeautifulSoup(html, 'html.parser')

        if url[len(self.ukgwa_prefix)-1:len(self.ukgwa_prefix)+2] != "/*/":
            return
        domain = url[len(self.ukgwa_prefix)+2:]

        accordions = soup.findAll("div", {"class": "accordion"})
        for acc in accordions:
            year = acc.find("span", {"class" : "year"})
            versions = acc.findAll("a", href=re.compile(".[1-2]*" + domain, re.IGNORECASE))
            for v in versions:
                snapshot = v['href'][1:15]
                entry = ["","","",snapshot,"","","200","0","","",""]
                version_list.append(" ".join(entry))

        return version_list

    def add_to_dict_list(self, D, key, value):
        if key in D:
            D[key].append(value)
        else:
            D[key] = [value]

    def read_cdx(self, returncodes = ['200','301']):

        if not self.success:
            return

        prev_checksum = '0'
        for row in self.return_list:
            fields = str(row)[2:-3].split(" ")
            if fields[4] not in returncodes:
                continue
            # row_dict not used but unable to test at moment
            #row_dict = {'snapshot':int(fields[1]), 'mime':fields[3], 'code':fields[4], 'checksum':fields[5]}
            entry = [int(fields[1]), fields[3], fields[4], fields[5], prev_checksum != fields[5]]
            prev_checksum = fields[5]
            self.min_snapshot = min(self.min_snapshot, entry[self.fields['SNAPSHOT']])  #row_dict['snapshot'])
            self.max_snapshot = max(self.max_snapshot, entry[self.fields['SNAPSHOT']])  #row_dict['snapshot'])
            self.snapshot_count += 1
            self.add_entry(entry[self.fields['SNAPSHOT']], entry)

if __name__ == '__main__':
    #mycdx = CDXReader("www.hm-treasury.gov.uk/d/sanctionsconlist.txt")
    mycdx = CDXReader("www.salt.gov.uk/industry_activity.html")
    mycdx.read_cdx()
    print(mycdx.index)
    for s in mycdx:
        print(s)
