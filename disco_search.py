import requests
from time import sleep
from urllib.request import urlopen
import re
from bs4 import BeautifulSoup
from ukgwa_view import UKGWAView
from ukgwa_textindex import UKGWATextIndex
import random
import networkx as nx
from operator import itemgetter


class DiscoView(UKGWAView):

    def __init__(self, page_limit=100, total_limit=1000, randomised=False):

        super().__init__()
        self.field_list = ["id", "parentId", "isParent", ["scopeContent", "description"]] # Discovery fields
        #self.field_list = ["id","coveringDates","coveringFromDate","coveringToDate","recordOpeningDate",["scopeContent","description"],
        #                   "closureType","citableReference","isParent"]
        self.page_limit = page_limit
        self.randomised = randomised
        self.ABSOLUTEMAX = 10000
        self.fields = {"IAID" : 0, "ParentId" : 1, "IsParent" : 2, "Description" : 3}
        self.sample_pct = 0.01
        self.min_sample = 10
        self.max_sample = 500

    def set_random(self, randomised):

        self.randomised = randomised

    def _page_iterator(self,series):

        batchStartMark = "*"
        more = True
        headers={"Accept": "application/json"}; #we want the API to return data in JSON format
        url="https://discovery.nationalarchives.gov.uk/API/records/children/" + series
        s=requests.Session(); #creating a session just groups the set of requests together

        while more:
            myparams={"limit": self.page_limit, "batchStartMark": batchStartMark}
            r=s.get(url, headers=headers, params=myparams); #send the url with our added parameters, call the response "r"
            r.raise_for_status(); #This checks that we received an http status 200 for the server response
            rjson=r.json()

            if rjson["hasMoreAfterLast"]:
                batchStartMark = rjson["assets"][-1]["sortKey"]
                print("Next batch:", batchStartMark, rjson["assets"][0]["id"])
            else:
                more = False
            yield rjson["assets"]


    def _sample_leaves(self, *series):

        crawl_ids = list(series)
        print("Crawl:",crawl_ids)
        total_retrieved = 0
        sample_data = []
        while len(crawl_ids) > 0:
            disco_id = crawl_ids.pop()
            retrieved = 0
            sample_count = 0
            for page in self._page_iterator(disco_id):
                if len(page) <= self.min_sample:
                    sample_size = len(page)
                else:
                    sample_size = int(len(page)*self.sample_pct)
                    sample_size = min(self.min_sample, sample_size)
                if sample_size == len(page):
                    sample = page
                else:
                    sample = random.sample(page, sample_size)
                print("Sample:",len(sample),"Retrieved:",retrieved)
                for s in sample:
                    save_fields = []
                    for f in self.field_list:
                        if isinstance(f,str):
                            field_value = s[f]
                        elif isinstance(f,list):
                            field_value = s[f[0]][f[1]] # could be recursive but for now it is only for the scope content description
                            field_value = self._clean_scope(field_value)
                        save_fields.append(field_value)
                    self.add_entry(s["id"], save_fields)
                    #out_fields.append(str(field_value).replace("\n"," ").replace("\r"," ").replace("  "," ").replace("|","~"))
 
                    if s["isParent"]:
                        crawl_ids.append(s["id"])

                sample_count += len(sample)
                retrieved += len(page)
                if sample_count >= self.max_sample:
                    break
            print("Id:", disco_id, "Count:", retrieved, "Total:", total_retrieved)
            total_retrieved += retrieved
            if total_retrieved > self.ABSOLUTEMAX:
                break
        print("Total =", total_retrieved)

    def _sample_to_graph(self):

        G = nx.DiGraph()

        for row in self:
            row_id = row[self.fields["IAID"]]
            parent_id = row[self.fields["ParentId"]]
            G.add_edge(row_id, parent_id)

        return G

    def _clean_text(self, text):
        new_text = text.replace("."," ").replace(","," ").replace("'","").replace(":"," ") \
                       .replace(";"," ").replace("-"," ").replace("("," ").replace(")"," ") \
                       .replace("["," ").replace("]"," ").replace("\n"," ")
        new_text = new_text.replace("`"," ")
        len_now = len(new_text)
        go = True
        while go:
            new_text = new_text.replace("  ", " ")
            if len_now == len(new_text):
                go = False
            else:
               len_now = len(new_text)
        return new_text

    def _clean_scope(self, scope):

        if scope is None:
            return ""
        soup = BeautifulSoup(scope, "html.parser")
        C = True
        while C:
            if soup.extref is None:
                C = False
                continue
            soup.extref.decompose()
        text = soup.findAll("p")
        this_text = ''
        for t in text:
            #print("\t",t.text)
            #print("\t\t",t)
            this_text += " " + t.text
        this_text = self._clean_text(this_text)

        return this_text

