import sys
import urllib.request, urllib.error
from bs4 import BeautifulSoup
from time import sleep
import random
import http.client as http
from ukgwa_view import UKGWAView


class UKGWASearch(UKGWAView):

    def __init__(self):

        super().__init__()

        self.RECORDLIMIT = 10000
        self.pg_size = 100
        self.max_page = 10
        self.SAMPLE_SIZE = 250
        self.MIN_SAMPLE = 2
        self.MAX_SAMPLE = 20
        self.SAMPLE_PCT = 0.1
        self.svd_k = 10
        self.web_prefix = 'https://webarchive.nationalarchives.gov.uk/'
        self.search_url = self.web_prefix + "search/result/"
        

    def search(self, search_string, random_pages = True):

        if len(search_string.split(" ")) > 1:
            print("Please stick to single word searches for now")
            return

        http.HTTPConnection._http_vsn = 10
        http.HTTPConnection._http_vsn_str = 'HTTP/1.0'


        site = ""
        page_counts = {}
        page_snapshots = {}
        domain_counts = {}
        first_page = {}
        page_count = 0
        pages_seen = set()


        domain_pages = {}
        page_list = [1]
        while len(page_list) > 0:
            pg = page_list.pop(0)
            this_page_links = 0
            search_page = self.search_url + "?q=" + search_string
            if len(site) > 0:
                search_page += "&site=" + site
            search_page += "&page=" + str(pg)
            search_page += "&amount=" + str(self.pg_size)
            if search_string == "olympics":
                search_page += "&site_exclude=getset.london2012.com"
            print(search_page)
            tries = 0
            found = False
            while tries < 3 and not found:
                try:
                    tries += 1
                    with urllib.request.urlopen(search_page) as f:
                        data = f.read().decode('utf-8')
                    found = True
                except urllib.error.HTTPError as e:
                    print("Retrying...",tries)
                    sleep(10)
    
            if not found:
                print("\tFailed to navigate to page")
                return
            soup = BeautifulSoup(data, "lxml")
            if pg == 1:
                print("Get count")
                counts = soup.findAll('span', {"class":"count"})
                result_count = -1
                for c in counts:
                    try:
                        result_count = int(c.text.replace(",",""))
                        break
                    except:
                        continue
                if result_count == -1:
                    print("No count found")
                    break
                page_limit = min(result_count, self.RECORDLIMIT)/self.pg_size
                int_page_limit = int(page_limit)
                leftover = int((page_limit - int_page_limit) * self.pg_size)
                print("Pages:",int_page_limit,"plus",leftover)
                if leftover > 0 and int_page_limit != 0:
                    page_list.append(int_page_limit+1)
                page_list += random.sample(list(range(2,int_page_limit)), min(self.max_page,int_page_limit-1))
                print(page_list)
            for anchor in soup.findAll('a', href=True):
                href = anchor['href']
                if href[0:len(self.web_prefix)] == self.web_prefix:
                    found_page = href[len(self.web_prefix):]
                    self.add_entry(found_page, found_page)

if __name__ == "__main__":
    S = UKGWASearch()
    S.search("salt")
