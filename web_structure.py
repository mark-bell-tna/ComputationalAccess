#!/usr/bin/python3

from bs4 import BeautifulSoup
from urllib.request import urlopen
from urllib.parse import urlparse
import re
import sys

class UKGWAStructure:

    def __init__(self):

        x = 1
        self.index = {}

    def loadurl(self, url, identifier = None):

        if identifier is None:
            identifier = url
        self.index[identifier] = self.parseurl(url)

    def parseurl(self, url):

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
    parsed = struc.parseurl("http://www.gov.uk/guidance")
    print(struc.domaintotree(parsed.netloc))
    print(struc.domaintotree(parsed.netloc, strip_www = True))
    print(struc.domaintotree(parsed.netloc, path = parsed.path, strip_www = True))
    exit()
    struc.loadurl("www.gov.uk", 5)
    print(struc.index)
    struc.loadurl("www.gov.uk")
    print(struc.index)

exit()

point_in_time = int(sys.argv[1])
SLASH_LIMIT = 0  # Number of slashes in the path of the url (after the domain) to consider. Filters out non-unique paths.
DEPTH = 2  # Max depth of graph search
THRESHOLD = 10  # Count limit for printing domain counts
TRIM_WWW = True  # Remove www prefix from websites 
prefix = "https://webarchive.nationalarchives.gov.uk"
atoz_url = "http://www.nationalarchives.gov.uk/webarchive/atoz/"
data_dir = "/home/research1/WEBARCH/5VIEWS/Data/"

atozfile = open(data_dir + 'ukgwa_atoz.txt','r')
cdx_file = open(data_dir + 'ukgwa_cdx.txt','r')
cdx_fields = next(cdx_file)
cdx_pages = {}
for row in cdx_file:
    fields = row[:-1].split("|")
    page = fields[0]
    snapshot = int(fields[1])
    if page in cdx_pages:
        min_max = cdx_pages[page]
        min_max[0] = min(min_max[0], snapshot)
        min_max[1] = max(min_max[1], snapshot)
    else:
        min_max = [snapshot, snapshot]
    cdx_pages[page] = min_max
#for k,v in cdx_pages.items():
#    print(k,v)
cdx_file.close()

non_web = {}
domain_graph = {}
done_urls = set()
for i,row in enumerate(atozfile):
    fields = row[:-1].split("|")
    if len(fields) != 2:
    #    print("No url:", row)
        continue
    title = fields[0]
    url = fields[1]
    website = url[len(prefix)+1:]
    if website[0] == "*":
        website = website[2:]
        if website not in cdx_pages:
            continue
        min_max = cdx_pages[website]
        if point_in_time < min_max[0] or point_in_time > min_max[1]:
            continue
        parsed = urlparse(website)
        #print("**************Parsed:",parsed,len(parsed.path.split("/")))
        netloc = parsed.netloc
        if TRIM_WWW and netloc[0:4] == "www.":
            netloc = netloc[4:]
        path = "/".join([p for p in parsed.path.split("/") if len(p) > 0][0:SLASH_LIMIT])
        if netloc + "/" + path in done_urls:
        #    print("Skipping",parsed)
            continue
        done_urls.add(netloc + "/" + path)
        if "catapult" in netloc:
            print(parsed)
        #print(netloc)
        parts = netloc.split(":")[0].split(".") # ":" is to remove ports from url
        parts.reverse()
        this_graph = domain_graph
        end = len(parts)-1
        for n,p in enumerate(parts):
            #print(p)
            if p not in this_graph:
                this_graph[p] = {}
            this_graph = this_graph[p]
            if n == end:
                if 'x-count' in this_graph:
                    this_graph['x-count'] += 1
                else:
                    this_graph['x-count'] = 1
            else:
                if 'x-children' not in this_graph:
                    this_graph['x-children'] = {}
                this_graph = this_graph['x-children']
        #print(domain_graph)
        #if i == 5:
        #    exit()
    else:
        #print(website.split("/")[0])
        folder = website.split("/")[0]
        if folder in non_web:
            non_web[folder] += 1
        else:
            non_web[folder] = 1

cdx_file.close()
atozfile.close()

print(non_web)

def domain_count(graph):
    count = 0
    if 'x-count' in graph:
        count += graph['x-count']
    if 'x-children' in graph:
        for g in graph['x-children'].values():
            count += domain_count(g)
    return(count)

def summarise_domains(domain_graph):
    stack = [[k, domain_graph[k], 0] for k in domain_graph.keys()]
    graph_levels = DEPTH+1
    current_position = ['*'] * graph_levels
    summary = []
    while len(stack) > 0:
        this_graph = stack.pop()
        key = this_graph[0]
        graph = this_graph[1]
        level = this_graph[2]
        current_position[level] = key
        current_position = current_position[:level+1] + (["*"] * (graph_levels-level-1))
        count = domain_count(graph)
        if count < THRESHOLD:
            continue
        print("\t"*level, ".".join([c for c in current_position if c != "*"]), key, count)
        summary.append([len(summary),point_in_time,".".join([c for c in current_position if c != "*"]), count])
        if level == DEPTH:
            continue
        if 'x-children' not in graph:
            print("No children")
            continue
        for k in graph['x-children'].keys():
            next_graph = graph['x-children'][k]
            stack.append([k, next_graph, level+1])
    return summary

summary = summarise_domains(domain_graph)
sum_file = open("domain_summary_" + str(point_in_time) + ".txt","w")
for row in summary:
    sum_file.write("|".join([str(x) for x in row]) + "\n")
sum_file.close()

