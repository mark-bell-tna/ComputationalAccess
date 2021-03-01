#!/usr/bin/python3

# TODO: if node does not branch record indices of run of descendents rather than creating branch that does not split
# This is to compress storage but makes the code more complex

from operator import itemgetter

class SuffixTree:

    token_list = ["ROOTNODE"]
    all_trails = []
    trail_summary = {}
    reference_list = []

    def __init__(self, position, stopwords = set()):

        self.children = []
        self.position = position
        self.length = 0
        self.stopwords = stopwords

    def add_tokens(self, tokens, reference = None):

        token_list = [t for t in tokens if t.lower() not in self.stopwords]
        if len(token_list) == 0:
            return
        token_list.append('$')
        for tok in token_list:
            SuffixTree.token_list.append(tok)
        start_pos = len(SuffixTree.token_list) - len(token_list)
        SuffixTree.reference_list.append([start_pos, len(token_list), reference])
        #print("Adding",tokens,start_pos)
        for i in range(len(token_list)):
            suffix = token_list[i:]
            self._add_suffix(suffix, start_pos+i, [])

    def _add_trail(self, trail):
        #print("\t\tAdd trail",trail)
        trail_summary = SuffixTree.trail_summary
        if trail[1] not in trail_summary:
            trail_summary[trail[1]] = {}
        if trail[2] not in trail_summary[trail[1]]:
            trail_summary[trail[1]][trail[2]] = set()
        trail_summary[trail[1]][trail[2]].add(trail[0])

    def _add_suffix(self, tokens, start_pos, trail):
        # TODO: for compactness, if a branch has no further branches then record the length of branch rather than create new nodes
        if len(tokens) == 0:
            return
        #print("Tok:",tokens,"St:",start_pos,"Trail:",trail)
        tok = tokens[0]
        if len(trail) == 0:
            this_trail = [start_pos,-1,0]
        else:
            this_trail = trail[:]
        found = False
        for ch in self.children:
            #print("\t\ttoken",tok,"position",ch.position)
            if SuffixTree.token_list[ch.position] == tok:  # Compare token to value in list lookup
                this_trail[1] = ch.position - this_trail[2]
                this_trail[2] += 1
                if len(tokens) > 1: # If there are still more to process
                    ch._add_suffix(tokens[1:], start_pos+1, this_trail) # recurse with current token removed and position in string incremented
                found = True  # Got a match
                break
        if not found: # no matching child node
            #print("\t\tNo match")
            #if this_trail[1] == -1:
            #    this_trail[1] = this_trail[0]
            if this_trail[2] == 0:
                this_trail[2] += 1
            if len(self.children) > 0:
                this_trail = []
            #    print("\t\tHas children")
            self.children.append(SuffixTree(start_pos))
            #elif:
            #    this_trail[1] = this_trail[0]
            #this_trail[2] += 1
            if len(tokens) > 1:
                self.children[-1]._add_suffix(tokens[1:], start_pos+1, this_trail)
        if len(this_trail) > 0 and this_trail[1] > -1:
            self._add_trail(this_trail)

    def printtree(self):

        nodes = [[self, 0]]
        while len(nodes) > 0:
            n = nodes.pop()
            print("\t" * n[1],n[0])
            for ch in n[0].children:
                nodes.append([ch, n[1]+1])

    def get_trails(self):
        return SuffixTree.all_trails

    def get_references(self):
        return SuffixTree.reference_list

    def _filter_trails(self, min_matches, min_length, max_length=1000):

        summary = []
        for k1,v1 in self.trail_summary.items():
            for k2,v2 in v1.items():
                if len(v2) < min_matches or (k2 < min_length or k2 > max_length):
                    continue
                tokens = [self.token_list[x] for x in range(k1,k1+max(k2,1))]
                if tokens[-1] == "$":
                    continue
                summary.append([tokens, len(v2), k1, max(k2,1),  v2])

        return summary

    def _collapse_trail(self, trail, min_matches):
        C_FLD = 1  # Match count field
        L_FLD = 3  # Token length field
        P_FLD = 2  # Position field
        M_FLD = 4  # Match list field

        trail.sort(key=itemgetter(L_FLD), reverse=True)
        process = True
        i = 0
        j = 1
        i_back = 0
        new_trail = []
        i_inserted = False
        inserts = dict()

        while process:
            if i >= len(trail):
                process = False
                continue
            if j >= len(trail):
                if i not in inserts:
                    new_trail.append(trail[i])
                    inserts[i] = len(new_trail)-1
                i += 1
                j = i+1
                continue
            start_i = trail[i][P_FLD]
            end_i = sum(trail[i][P_FLD:P_FLD+2])-1
            start_j = trail[j][P_FLD]
            end_j = sum(trail[j][P_FLD:P_FLD+2])-1
            if trail[i][L_FLD] == trail[j][L_FLD]:
                j += 1
                continue
            if trail[i][L_FLD] - trail[j][L_FLD] > 1:
                if i not in inserts:
                    new_trail.append(trail[i])
                    inserts[i] = len(new_trail)-1
                i += 1
                j = i+1
                continue

            if self.token_list[start_i] == self.token_list[start_j]:
                #print("**************gotta left match***************", start_i, start_j, ST.token_list[start_j])
                #print("\t",topN[i])
                #print("\t",topN[j])
                matched = True
                offset = 1
                while offset < trail[j][L_FLD]:
                    #print("\t",ST.token_list[start_i+offset], ST.token_list[start_j+offset])
                    if self.token_list[start_i+offset] == self.token_list[start_j+offset]:
                        offset += 1
                        continue
                    matched = False
                    break
                if matched:
                    #print("\tLeft match")
                    #print("\t",topN[i])
                    #print("\t",topN[j])
                    if j in inserts:
                        updated_j = new_trail[inserts[j]]
                    else:
                        updated_j = [trail[j][0], 0, -1, -1, trail[j][M_FLD]]
                    updated_matches = updated_j[M_FLD].difference([x for x in trail[i][M_FLD]])
                    #print("\tAfter",updated_matches)
                    #if len(updated_matches) >= THRESHOLD:
                    updated_j[C_FLD] = len(updated_matches)
                    updated_j[P_FLD] = trail[j][P_FLD]
                    updated_j[L_FLD] = trail[j][L_FLD]
                    updated_j[M_FLD] = updated_matches
                    if j in inserts:
                        #print("\tUpdated",j,len(updated_matches),updated_j)
                        new_trail[inserts[j]] = updated_j
                    else:
                        #print("\tInserted",j,len(updated_matches),updated_j)
                        new_trail.append(updated_j)
                        inserts[j] = len(new_trail)-1

                j += 1
                continue

            elif self.token_list[end_i] == self.token_list[end_j]:
                #print("**************gotta right match***************", end_i, end_j, self.token_list[end_i])
                #print("\t",topN[i])
                #print("\t",topN[j])
                matched = True
                offset = 1
                while offset < trail[j][L_FLD]:
                    #print("\t",ST.token_list[end_i-offset], ST.token_list[end_j-offset])
                    if self.token_list[end_i-offset] == self.token_list[end_j-offset]:
                        offset += 1
                        continue
                    matched = False
                    break
                if matched:
                    #print("Right match")
                    #print("\t",topN[i])
                    #print("\t",topN[j])
                    if j in inserts:
                        updated_j = new_trail[inserts[j]]
                    else:
                        updated_j = [trail[j][0], 0, -1, -1, trail[j][M_FLD]]
                    updated_matches = updated_j[M_FLD].difference([x+1 for x in trail[i][M_FLD]])
                    #print("\tAfter",updated_matches)
                    #if len(updated_matches) >= THRESHOLD:
                    updated_j[C_FLD] = len(updated_matches)
                    updated_j[P_FLD] = trail[j][P_FLD]
                    updated_j[L_FLD] = trail[j][L_FLD]
                    updated_j[M_FLD] = updated_matches
                    if j in inserts:
                        #print("\tInserted",j,len(updated_matches),updated_j)
                        new_trail[inserts[j]] = updated_j
                    else:
                        #print("\tUpdated",j,len(updated_matches),updated_j)
                        new_trail.append(updated_j)
                        inserts[j] = len(new_trail)-1
    
                j += 1
                continue
    
            j += 1

        return [t for t in new_trail if t[1] >= min_matches]



#************************************************************************************************************************

    def __str__(self):
        #return str(self.this_position)
        return SuffixTree.token_list[self.position]

if __name__ == "__main__":

    sf = SuffixTree(0)
    sf.add_tokens(["while","shepherds","watched","their","sheep","by","night"])
    sf.add_tokens(["while","shepherds","watched","tv","at","night"])
    sf.add_tokens(["while","shepherds","watched","tv","at","night"])
    sf.add_tokens(["red","sky","etc"])
    #sf.add_tokens(["red","sky","etc"])
    #sf.add_tokens(["red","sky","etc"])
    sf.add_tokens(["red"])
    sf.add_tokens(["red"])
#    sf.add_tokens(["red"])
    sf.add_tokens(["red","red","robin"])
    sf.add_tokens(["red","sky","etc"])
    sf.add_tokens(["papa","alpha","papa","alpha"])
    sf.add_tokens(["papa","alpha","papa"])

    print(SuffixTree.token_list)
    #sf.printtree()
                
    #trails = sf.get_trails()
    #print(trails)
    #trail_summary = {}
    #for t in trails:
    #    if t[1] not in trail_summary:
    #        trail_summary[t[1]] = {}
    #    if t[2] not in trail_summary[t[1]]:
    #        trail_summary[t[1]][t[2]] = set()
    #    trail_summary[t[1]][t[2]].add(t[0])

        #print([SuffixTree.token_list[x] for x in range(t[0],t[0]+t[2])], t[2])

    trail_summary = sf.trail_summary
    print(trail_summary)
    for k1,v1 in trail_summary.items():
        print("Key",k1,"Vals",v1)
        for k2,v2 in v1.items():
            print("\tCounts:",[SuffixTree.token_list[x] for x in range(k1,k1+max(k2,1))], v2)
            #print("Counts:",[x for x in range(k1,k1+k2+1)], k1,v1,k2,v2)

