#!/usr/bin/python3

from ukgwa_view import UKGWAView
from ukgwa_textindex import UKGWATextIndex
from disco_search import DiscoView
import networkx as nx
from operator import itemgetter

if __name__ == "__main__":
    #field_list = ["id","coveringDates","coveringFromDate","coveringToDate","recordOpeningDate",["scopeContent","description"],
    #              "closureType","citableReference","isParent"]
    series_list = [[x,0] for x in ['A13530124']]
    D = DiscoView(page_limit=500)
    D.min_sample=20
    D.sample_pct=0.05
    #S = D._sample_leaves('A13530124')
    #D._sample_leaves('C188', 'C142','C201','C287')
    #D._sample_leaves('A13530124')
    D._sample_leaves('C14303')  # WO 95
    G = D._sample_to_graph()
    T = UKGWATextIndex(stop_words = ["", "and", "of", "the", "in", "a", "by", "which", "their","as","an",
                                     "for","to","if","be","this","on","are","at","were","it","is","that",
                                     "from","been","has","have","or","there","was","they","with","these"])

    for idx in D:
        desc = D.get_field(idx, "Description")
        if desc is None:
            continue
        T.add_tokens(D.get_field(idx, "Description").split(" "), idx)
    P = T.get_phrases(9,1,5)
    P.sort(key=itemgetter(1), reverse=False)
    for p in P:
        print(p)

    nx.write_gml(G, '/home/dataowner/vn_share/GephiGraphs/disco_sample.gml')

