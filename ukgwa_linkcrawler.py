#!/usr/bin/python3

import hashlib
import os
import sys
import time
import re
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from http.client import IncompleteRead

from cdx_reader import CDXReader

from socket import error as SocketError
import bs4
from bs4 import BeautifulSoup
import grequests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests_futures.sessions import FuturesSession
import pickle
from operator import itemgetter
from os.path import isdir
from os import mkdir
from networkx.algorithms.dag import topological_sort
import networkx as nx
from os.path import isfile

class Crawl:

    def __init__(self, url, user_agent, save_output=False, refresh=True,
                 data_folder = "./", hash_function = hashlib.md5, max_text_length = 30, folder_partitions=5):
        self.url = url
        self.ukgwa_protocol = "https://"
        self.ukgwa_prefix = "webarchive.nationalarchives.gov.uk/"
        self.snap_re = re.compile("[0-9]{14}")
        self.data_folder = data_folder
        self.save_root = data_folder
        self.set_site(url)
        self.max_text_length = max_text_length
        self.user_agent = user_agent
        self.folder_partitions = folder_partitions
        self.hash_function = hash_function
        self.link_counts = {}
        self.html = self.get_page(url)
        self.soup = self.get_soup(self.html[1])
        self.links = self.get_html_links(self.soup, url)
        self.snap_format = "99999999999999"
        self.executor = ThreadPoolExecutor(max_workers=50)
        #self.session = FuturesSession(executor=ThreadPoolExecutor(max_workers=100))
        self.url_list = []
        self.new_urls = []
        self.rejects = set()
        self.crawled = set()
        self.site = ''
        self.snapshot = ''
        self.protocol = 'http:'
        self.viewed = 0
        self.added = 0
        self.earliest_links = {}
        self.links_filter = set()
        self.fixed_snapshot = False
        self.site_labels = {}
        self.text_folder = {'name' : "TEXTHASHES", 'subfolders' : self.folder_partitions}
        self.setup_folders(self.text_folder)
        self.link_folder = {'name' : "LINKHASHES", 'subfolders' : self.folder_partitions}
        self.setup_folders(self.link_folder)
        self.html_folder = {'name' : "HTML", 'subfolders' : self.folder_partitions}
        self.setup_folders(self.html_folder)

    def setup_folders(self, folder):
        if not os.path.isdir(folder['name']):
            os.mkdir(folder['name'])
        for i in range(folder['subfolders']):
            new_folder = folder['name'] + "/" + str(i)
            if not os.path.isdir(new_folder):
                os.mkdir(new_folder)

    def get_hash_partition(self, hash_value):
        return int(hash_value, 16) % self.folder_partitions

    def get_hash(self, value):
        if value is None:
            value = ""
        H = self.hash_function()
        H.update(repr(value).encode('utf-8'))
        return H.hexdigest()

    def _write_to_file(self, output_file, text):
        save_file = open(output_file,"w")
        save_file.write(text)
        save_file.close()

    def save_text(self, text, hash_value, node_type):
        sub_folder = str(get_hash_partition)
        save_file = self.text_folder['name'] + "/" + sub_folder + "/" + str(hash_value) + ".txt"
        self._write_to_file(save_file, text)

    def save_link(self, link, hash_value, node_type):
        sub_folder = str(get_hash_partition)
        save_file = self.link_folder['name'] + "/" + sub_folder + "/" + str(hash_value) + ".txt"
        self._write_to_file(save_file, link)

    # Increment counter dictionary
    def add_to_dict(self, D, k, v = 1):
        if k in D:
            D[k] += v
        else:
            D[k] = v

    def set_protocol(self, protocol):
        self.protocol = protocol + ":"

    def set_snapshot(self, snapshot):
        self.snapshot = snapshot
        self.mk_snap_dir()

    # mk_site_dir, mk_snap_dir, set_folder_partitions, set_size all set up the
    # directory structure for writing data to
    def mk_site_dir(self):
        if len(self.site) == 0:
            return
        site_dir = self.save_root + self.site
        #if not isdir(site_dir):
        #    mkdir(site_dir)
        
    def set_root(self, folder):
        self.save_root = folder
        if folder[-1] != "/":
            self.save_root += "/"

    def mk_snap_dir(self):
        if len(self.snapshot) == 0:
            return

        self.mk_site_dir()
        snap_dir = self.save_root + self.site + "/" + self.snapshot
        #if not isdir(snap_dir):
        #    mkdir(snap_dir)

    # Allows partitioning of files into sub folders to reduce size of any one folder
    def set_folder_partitions(self, folder_partitions):
        self.folder_partitions = folder_partitions
        if self.snapshot == '':
            return
        #batch_root = self.save_root + self.site + "/" + self.snapshot + "/"

    def set_site(self, url):
        site = self.get_url_parts(url)
        self.site = site[0].netloc
        if self.site[0:4] == "www.":
            self.site_suffix = self.site[4:]
        else:
            self.site_suffix = self.site
        self.mk_site_dir()

    def set_data_folder(self, folder):
        self.data_folder = folder
        if folder[-1] != "/":
            self.data_folder += "/"
    
    # Uses urlparse to split url into constituent parts
    # Pre-processes url to remove ukgwa address and snaphot if present
    # Return value is a list containing the ParseResult object (see urllib) and the snapshot value
    def get_url_parts(self, url):
        prefix_pos = url.find(self.ukgwa_prefix)
        if prefix_pos >= 0:
            this_url = url[prefix_pos+len(self.ukgwa_prefix):]
        else:
            this_url = url
        snap_match = re.search(self.snap_re, this_url)
        if snap_match is None:
            snapshot = ''
        else:
            snapshot = this_url[snap_match.start():snap_match.end()]
            this_url = this_url[snap_match.end()+1:]
        try:
            url_parts = urlparse(this_url)
        except Exception as e:
            self.rejects.add(this_url)
            print("Error:",e,this_url)
            return [urlparse("https://www.dummyurl.com/abcdef"), self.snapshot]

        return [url_parts, snapshot]

    def rebuild(self, url, snapshot):
        if isinstance(url, str):
            this_url = url
        else:
            this_url = urlunparse(url)
        
        if this_url[0:4] != "http":
            return("https://" + self.ukgwa_prefix + "/" + snapshot + "/" + self.protocol + "//" + this_url)
        else:
            return("https://" + self.ukgwa_prefix + "/" + snapshot + "/" + this_url)

    def load_url(self, url, timeout):
        page =  urlopen(Request(url, headers={'User-Agent': self.user_agent}))
        return page

    def get_page_list(self, url_list):

        futures = {self.executor.submit(self.load_url, u, 20): u for u in url_list}  #{self.session.get(u) for u in url_list}
        results = []
        self.viewed += len(url_list)
        has_errors = False
        for future in as_completed(futures):
            try:
                resp = future.result()
                results.append(resp)
            except Exception as  e:
                has_errors = True
                print("Error fetching:",e, futures[future])
                self.rejects.add(futures[future])
                continue
        #if has_errors:
        #    print(url_list)
        return results

    def add_url(self, url):
        self.url_list.append(url)

    def process_urls(self, more_links = True):
        
        while len(self.url_list) > 0:
            these_urls = self.url_list[0:self.folder_partitions]
            self.url_list = self.url_list[self.folder_partitions:]
            responses = self.get_page_list(these_urls)
            #print("Time start:",time.time())
            for r in responses:
                #if 'content-type' not in r.headers:
                #    print("No content type",r)
                #    continue
                content_type = r.info().get_content_maintype() #r.headers['Content-Type'].split(";")[0].strip()
                filter = self.filter_pages(r.getcode(), content_type)
                if filter == 1:
                    #print("\tLink:",r.url)
                    parts = self.get_url_parts(r.url)
                    new_url = parts[0].netloc + "/" + parts[0].path
                    new_url = parts[0].scheme + "://" + new_url.replace("//","/")
                    if new_url not in self.crawled:
                        #print("*********Adding",new_url)
                        self.added += 1
                        if self.added % 100 == 0:
                            print("Viewed:",self.viewed,"Added:",self.added,"Time:",time.time())
                        self.sitemap.add_phrase(new_url)
                        self.crawled.add(new_url)
                        try:
                            html = r.read()
                        except (IncompleteRead) as e:
                            continue
                        soup = self.get_soup(html)
                        if more_links:
                            links = self.get_html_links(soup, new_url)
                            for l in links:
                                if l not in self.rejects:
                                    #if "DG_183733" in l:
                                    #    print("Add DG_183733:", l)
                                    self.new_urls.append(l)
                else:
                    print("**********Out:",r.geturl(), r.getcode(), content_type)
            #print("Time end:",time.time())

    def crawl_versions(self,url,url_file="",skip_list = set()):

        version_list = []
        try:
            html = urlopen(url)
        except Exception as e:
            print("Error with URL:",url)
            print(e)
            return
        soup = BeautifulSoup(html, 'html.parser')
        #print(soup)

        if url[len(prefix)-1:len(prefix)+2] != "/*/":
            print("Different format:",url,url[len(prefix)-1:len(prefix)+2])
            return
        domain = url[len(prefix)+2:]

        #out_file = open(url_file,"a")
        accordions = soup.findAll("div", {"class": "accordion"})
        print("Dom:",domain)
        print("Url:",url,"Accordions:",len(accordions))
        for acc in accordions:
            year = acc.find("span", {"class" : "year"})
            #print("Acc:",acc)
            print("\tYear", year, year.text,domain)
            versions = acc.findAll("a", href=re.compile(".[1-2]*" + domain, re.IGNORECASE))
            for v in versions:
                print("\t\t",v['href'])
                version_list.append(v['href'])
                #out_file.write(domain + "|" + year.text +  "|" + v['href'] + "\n")
        #out_file.close()
        return version_list

    def get_page(self, url, refresh=True):
        url_hash = self.get_hash(url)
        hash_partition = self.get_hash_partition(url_hash)
        try:
            html = urlopen(Request(url, headers={'User-Agent': self.user_agent}))
        except HTTPError as e:
            print("HTTP Error:",e.code,url)
            return [e.code, None]
        except URLError as e:
            print("URL:",e.code)
            print(url)
            return [e.code, None]
        else:
            return [html.status, html]
            

    def filter_pages(self, page_status, page_type, return_types = [200], page_types = ['text/html','text']):
        if page_status not in return_types:
            return -1
        if page_type not in page_types:
            return -1
        return 1

    def get_soup(self, html):

        try:
            soup = BeautifulSoup(html, 'html.parser')
        except SocketError as e:
            if e.errno != errno.ECONNRESET:
                raise # Not error we are looking for
            return # Handle error here.

        #print(soup.find_all('title'))
        #links = [l for l in soup.find_all('a', href=True)]
        #for l in links:
        #    if l['href'][0] == '#':
        #        continue
        #    print(l['href'])

        return soup
 
    def get_html_links(self, soup, parent, filter = set(), return_orig = False):
        page_links = []
        links = [l for l in soup.find_all('a', href=True)]
        parent_parts = self.get_url_parts(parent)
        #print("Parent:",parent_parts)
        for ln in links:
            if len(ln['href']) == 0:
                continue
            if '#' in ln['href'][0]:
                continue
            if ln['href'].find("javascript") >= 0:
                continue
            if ln['href'].find("mailto") >= 0:
                continue
            parts = self.get_url_parts(ln['href'].strip())
            link_url = parts[0]
            #print("\tLink:",ln)
            #print("\t\tPath:",link_url.netloc,link_url.path)
            snapshot = parent_parts[1]
            if_path = 0
            if link_url.netloc == '':
                this_url = parent_parts[0].netloc + "/" + link_url.path
            else:
                link_domain = link_url.netloc
                if link_domain[:4] == "www.": link_domain = link_domain[4:]
                #print("Link domain",link_domain,"Suffix",self.site_suffix)
                #if link_domain != self.site_suffix:
                #    continue
                if_path += 1
                this_url = link_url.netloc + link_url.path
            #if "DG_183713" in this_url:
            #    print("P:", parent_parts[0].netloc, "U:",link_url.path)
            #    print("Gen URL:", this_url, "If:",if_path)
            #print("URL:",this_url)
            self.add_to_dict(self.link_counts, this_url)
            #parent_page = parent_parts[0].netloc
            #if this_url in self.earliest_links:
            #    earliest_url = self.earliest_links[this_url]
            #    earliest_split = earliest_url.split("/")
            #    parent_split = parent_page.split("/")
            #    if len(parent_split) < len(earliest_split):
            #        self.earliest_links[this_url] = parent_page
            #else:
            #    self.earliest_links[this_url] = parent_page
            #this_url = self.rebuild(this_url, snapshot) # TODO: change to link_url
            base_url = this_url[8+len(self.ukgwa_prefix)+16:]
            if base_url not in filter:
                if return_orig:
                    page_links.append([this_url, ln])
                else:
                    page_links.append(this_url)

        return page_links

    def url_to_filename(self, url):
        parts = self.get_url_parts(url)
        new_url = parts[0].netloc + "/" + parts[0].path
        new_url = parts[0].scheme + "://" + new_url.replace("//","/")
        snapshot = parts[1]
        filename = new_url.replace(":","").replace("/","_")
        filename = snapshot + "_" + filename
        return filename[:245] + ".txt"

    def write_soup_to_file(self, soup, folder, filename, url):

        html_links = self.get_html_links(soup, parent = url, filter = self.links_filter, return_orig = True)   
        print("Writing to:", folder + filename)
        page_file = open(folder + filename,"w")
        to_keep = dict([(l[1],l[0][8+len(self.ukgwa_prefix)+16:]) for l in html_links])
        links = [l for l in soup.find_all('a', href=True)]
        for l in links:
            try:
                if l not in to_keep:
                    l.decompose()
            except:
                print("Error decomposing link")
            #else:
            #    print("Keeping:",to_keep[l])
        S = [[soup,'abc']]
        #print(S)
        soup_text = soup.find_all(text=True)
        for t in soup_text:
            if len(t.strip()) > 0:
                page_file.write(t + "\n")
        #while len(S) > 0:
        #   ch = [c for c in S[0][0].children]
        #   parent = S[0][0]
        #   S = S[1:]
        #   #print("Children:",len(ch))
        #   for c in ch:
        #       #print("\nName:",c.name,"Type:",type(c))
        #       if type(c) is bs4.element.NavigableString:
        #           text = c.string.replace("\n","")
        #           if len(text) > 0:
        #               #print("\t\t","Nav",str(c),parent.name)
        #               if parent.name != "script":
        #                   page_file.write(text + "\n")
        #       elif type(c) is bs4.element.Tag:
        #           if c.name != "a":
        #               S.append([c,parent])
        #           #if c.name == "a":
        #           #    #print(c.get('href'),"is a",c.name)
        page_file.close()
                
    def snap_filter(self, snapshot):
        this_year = int(snapshot[0:4])
        snap_year = int(self.snapshot[0:4])
        print("Filtering:",this_year,snap_year)
        if self.fixed_snapshot:
            if snapshot[0:6] != self.snapshot[0:6]:
                return False
        if this_year == snap_year:
            return True
        if snap_year - this_year == 1:
            return True
        return False

    def urls_to_files(self, folder):

        print("URLS to write:",len(self.url_list))
        while len(self.url_list) > 0:
            these_urls = self.url_list[0:self.folder_partitions]
            self.url_list = self.url_list[self.folder_partitions:]
            responses = self.get_page_list(these_urls)
            #print("Time start:",time.time())
            for i,r in enumerate(responses):
                url = r.geturl()
                parts = self.get_url_parts(url)
                this_snap = parts[1]
                if not self.snap_filter(this_snap):
                    continue
                html = r.read()
                soup = self.get_soup(html)
                filename = self.url_to_filename(r.geturl())
                self.write_soup_to_file(soup, self.data_folder + str(i) + "/", filename, r.geturl())
        
    def load_pickles(self):
        try:
            self.sitemap.ngram_paths = pickle.load(open('crawler_ngram_' + self.site + "." + self.snapshot + '.pck','rb'))
        except:
            print("Not loaded")
        try:
            self.new_urls = pickle.load(open('crawler_new_urls_' + self.site + "." + self.snapshot + '.pck','rb'))
        except:
            print("Not loaded")
        try:
            self.link_counts = pickle.load(open('crawler_link_counts_' + self.site + "." + self.snapshot + '.pck','rb'))
        except:
            print("Not loaded")
        try:
            self.earliest_links = pickle.load(open('crawler_earliest_links_' + self.site + "." + self.snapshot + '.pck','rb'))
        except:
            print("Not loaded")
        
    def save_pickles(self):
        pickle.dump(self.sitemap.ngram_paths,open('crawler_ngram_' + self.site + "." + self.snapshot + '.pck','wb'))
        pickle.dump(self.new_urls, open('crawler_new_urls_' + self.site + "." + self.snapshot + '.pck','wb'))
        pickle.dump(self.link_counts, open('crawler_link_counts_' + self.site + "." + self.snapshot + '.pck','wb'))
        pickle.dump(self.earliest_links, open('crawler_earliest_links_' + self.site + "." + self.snapshot + '.pck','wb'))

    def bf_all_paths(self):
        BF = self.sitemap.breadth_first([protocol + ":",self.site])
        paths = set()
        path = protocol + "://" + self.site
        paths.add(path)
        for pages in BF:
            path = protocol + "://" + self.site
            for p in pages:
                path += "/" + p
                paths.add(path)
        return(list(paths))
    
    def graph_from_soup(self, soup):

        G = nx.DiGraph()

        node_dict = {}
        all_nodes = []
        all_nodes.append([0,soup.html])
        node_dict[soup.html] = 0
        parent_count = {}
        counter = 0
        node_id = 0
        p_id = -1
        while len(all_nodes) > 0:
            is_text = False
            all_sections = False
            N = all_nodes.pop()
            p_id = N[0]
            N = N[1]
            #if N.name not in ["html","script"]:
            #    print("Node:",counter,N,"Name:",N.name,"String:",N.string)
            #    break
            counter += 1
            #if p_id == -1:
            #    p_id = 0
            #else:
            #    p_id = N.parent
            #p_id = N.parent
            #print(type(p_id), type(N))
            #exit()
            #if N.parent in node_dict:
            #    p_id = node_dict[N.parent]
            #else:
            #    p_id = -1
            text_length = 0
            if p_id not in parent_count:
                parent_count[p_id] = 1
            else:
                parent_count[p_id] += 1
            if N.name == "script":
                content = ""
                node_label = ""
                node_hash = self.get_hash(node_label)
                node_type = "script"
                continue
            elif N.name in ["p","h1","h2","h3", "li"]:
                content = N.get_text()
                text_length = len(content)
                node_label = content[0:self.max_text_length]
                node_hash = self.get_hash(content)
                node_type = N.name
                is_text = True
                if text_length > self.max_text_length:
                    self.save_text(content, node_hash, node_type)
            elif N.name == "a":
                href = N.get('href')
                if href is None:
                    href = ""
                node_type = "link"
                if N.string is None:
                    content = "|"+href
                    node_label = ""
                    node_hash = self.get_hash(href)
                else:
                    content = N.string+"|"+href
                    node_label = N.string
                    text_length = len(node_label)
                    if node_label == "All sections":
                        print(node_label)
                        all_sections = True
                    node_hash = self.get_hash(N.string)
                self.save_link(content, node_hash, node_type)

            else:
                node_type = N.name
                if len(node_type) == 0:
                    node_type = "blank"
                content = N.string
                if content is None:
                    content = ""
                text_length = len(content)
                node_label = ""
                node_hash = self.get_hash(content)
                if text_length > self.max_text_length:
                    self.save_text(content, node_hash, node_type)
                #if content == None:
                #    node_label = ""
                #else:
                #    node_label = content[0:20]
            #print(node_dict[N], N.name, p_id,  N.parent.name, content)
            #if "clientSide" in node_label: #Filter these out for now
            #    continue
 
            node_id += 1
            if node_label not in self.site_labels:
                self.site_labels[node_label] = len(self.site_labels)
            standardised_label = node_id #self.site_labels[node_label]

            if p_id not in G:
                G.add_node(p_id, name="root", sitenameid=standardised_label,  tag=N.parent.name, nodetype = node_type, nodehash = self.get_hash("root"), text_length = text_length)
            if node_id not in G:  #if node_dict[N] not in G:
                #G.add_node(node_dict[N], name=node_label, sitenameid=standardised_label, tag=N.name, nodetype = node_type, nodehash = self.get_hash(node_label))
                G.add_node(node_id, name=node_label, sitenameid=standardised_label, tag=N.name, nodetype = node_type, nodehash = self.get_hash(node_label), text_length = text_length)
            #if p_id != node_dict[N]:
            if p_id != node_id:
                #if is_text and "23 June" in content:
                #    print(N.name, node_hash, "Content =",content)
                #    print(is_text, p_id, node_label, nx.get_node_attributes(G, p_id), node_id, nx.get_node_attributes(G, node_id))
                G.add_edge(p_id, node_id)
            C = N.children
            for i,c in enumerate(C):
                if c.name is not None:
                    all_nodes.append([node_id,c])
                    node_dict[c] = node_id #len(node_dict)

        #print(self.site_labels)
        return G

    def collapse(self, G):
        T = topological_sort(G)

        prev = None
        to_collapse = []
        for t in T:
            if len(G[t]) == 1:
                parents = [p for p in G.predecessors(t)]
                if len(parents) == 0:
                    continue
                if "name" in G.nodes[t]:
                    if len(G.nodes[t]["name"]) > 0:
                        continue
                to_collapse.append([[parents[0],t,k] for k in G[t]])
            if len(G[t]) == 0:
                if "name" in G.nodes[t]:
                    if len(G.nodes[t]["name"]) == 0:
                        G.remove_node(t)
                else:
                    G.remove_node(t)

        renamed = {}
        for TC in [x[0] for x in to_collapse]:
            for i in range(len(TC)):
                if TC[i] in renamed:
                    TC[i] = renamed[TC[i]]
            #print("TC:",TC)
            if G.has_node(TC[0]) and G.has_node(TC[2]):
                G.add_edge(TC[0], TC[2])
            renamed[TC[1]] = TC[0]
            G.remove_node(TC[1])

    def load_labels(self, label_file):
        if isfile(label_file):
            self.site_labels = pickle.load(open(label_file, "rb"))
        else:
            self.site_labels = {}
        
    def save_labels(self, label_file):
        pickle.dump(self.site_labels, open(label_file, "wb"))

if __name__ == "__main__":


    #from gevent import monkey
    #monkey.patch_all()

    prefix = "https://webarchive.nationalarchives.gov.uk/"
    site = "www.gov.uk"
    snapshot = 20200701065627
    path = "/browse/neighbourhoods"
    path = "/government/publications/coronavirus-outbreak-faqs-what-you-can-and-cant-do/coronavirus-outbreak-faqs-what-you-can-and-cant-do"
    protocol = "https"
    url = prefix + str(snapshot) + "/" + protocol + "://" + site + path
    #md5 = hashlib.md5()
    #md5.update(url.encode('utf-8'))
    #url_hash = md5.hexdigest()

    C = Crawl(url, user_agent='MB Research')
    print(C.links)
    exit()
    C.set_site(site)
    #if os.path.isfile("HTML/" + url_hash + ".html"):
    #    with open("HTML/" + url_hash + ".html", "r", encoding='utf-8') as file:
    #        html = file.read()
    #        html = [200, html]
    #        #print("Read html from file", url_hash)
    #else:
    #    html = C.get_page(url)
    soup = C.get_soup(html[1])
    if not os.path.isfile("HTML/" + url_hash + ".html"):
        with open("HTML/" + url_hash + ".html", "w", encoding='utf-8') as file:
            file.write(str(soup))
    links = C.get_html_links(soup, url)
    G = C.graph_from_soup(soup)

    #nx.write_gml(G, url_hash + ".gml")


