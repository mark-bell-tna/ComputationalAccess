from bs4 import BeautifulSoup
from urllib.request import urlopen
import re

class UKGWAIndex:

    def __init__(self):

        self.index = {}
        self.discoverylookup = {}
        self.iterindex = 1
        self.maxindex = 0
        self.filedelimiter = "|"
        self.ukgwa_prefix = "https://webarchive.nationalarchives.gov.uk/"
        self.atoz_url = "http://www.nationalarchives.gov.uk/webarchive/atoz/"
        self.id_prefix = "UKGWA"

    def indexfromfile(self, filepath):

        atozfile = open(filepath, 'r')
        for row in atozfile:
            fields = row[:-1].split(self.filedelimiter)
            self.index[fields[0]] = fields
        self.maxindex = len(self.index)
        atozfile.close()

    def indextofile(self, filepath):
        
        indexfile = open(filepath, 'w')
        for idx in self:
            indexfile.write(self.filedelimiter.join([str(x) for x in idx]))
            indexfile.write("\n")
        indexfile.close()

    def discoveryfromfile(self, filepath):

        discoveryfile = open(filepath, 'r')
        discoveryfile.close()

    def matchukgwatodiscovery(self):

        for v in self.index.values():
            url = v[2]
            if url in self.discoverylookup:
                v[3] = self.discoverylookup[url]

    def indexfromweb(self):

        # Should read these from project parameters eventually

        html = urlopen(self.atoz_url)
        soup = BeautifulSoup(html, 'html.parser')

        links = soup.findAll("a", href=re.compile(self.ukgwa_prefix))

        row_id = 0
        for link in links:
            href = link['href']
            href = href[len(self.ukgwa_prefix):]
            category = href.split("/")[0]
            href = href[len(category)+1:]
            if len(href) == 0:
                continue
            row_id += 1
            reference = self.id_prefix + "." + str(row_id)
            self.index[reference] = [reference, link.text.replace("\n"," ").strip(), category, href, 'N']
        self.maxindex = row_id

    def indexlookup(self, key):
        if key in self.index:
            return self.index[key]
        return []

    def __iter__(self):
        self.iterindex = 1
        return self

    def __next__(self):
        if self.iterindex > self.maxindex:
            raise StopIteration

        next_reference = self.id_prefix + "." + str(self.iterindex)
        self.iterindex += 1
        return self.index[next_reference]

if __name__ == "__main__":

    idx = UKGWAIndex()
    idx.indexfromweb()
    idx.indextofile("testatozfile.txt")

    print(idx.indexlookup("UKGWA.5"))
