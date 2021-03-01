#!/usr/bin/python3

# TODO: if node does not branch record indices of run of descendents rather than creating branch that does not split
# This is to compress storage but makes the code more complex

from operator import itemgetter
from bisect import bisect_left
import random

debug = False

def debugprint(*value):
    if debug:
        print(*value)

class TreeNode:

    def __init__(self, position, length, leaf=False):

        debugprint("Creating node",position,"length",length)
        self.position = position
        self.length = length
        self.is_leaf = leaf
        self.children = []
        self.branch_size = 0 # total leaf children

    def get_branch_size(self,update=False):

        if self.is_leaf:
            return len(self.children)
        if not update and self.branch_size > 0:
            return self.branch_size
        branch_size = 0
        for ch in self.children:
            branch_size += ch.get_branch_size()
        self.branch_size = branch_size
        return branch_size

    def get_tree_size(self):

        if self.is_leaf:
            return 1
        branch_size = 0
        for ch in self.children:
            branch_size += ch.get_tree_size()
        return branch_size

    def set_leaf(self, value):
        self.is_leaf = value

    def get_children(self):
        return self.children

    def add_child(self, position, length, is_leaf=True):
        self.children.append(TreeNode(position, length, is_leaf))

    def __repr__(self):
        return "Pos:" + str(self.position) + ", Len:" + str(self.length)

class SuffixTree:

    #def __init__(self, position, length = 0, reference_list = [], reference_lookup = {}, trail_summary = {},
    #        all_trails = [], token_list = ["ROOTNODE"], stopwords = set()):
    def __init__(self, stopwords=set(), eol_symbol = '$'):

        self.tree = TreeNode(0, 1)
        #self.position = position
        #self.length = length
        self.stopwords = stopwords
        self.eol_symbol = eol_symbol
        self.token_lookup = {}
        self.lookup_count = 0
        self.token_list = ["ROOTNODE"]  #token_list
        #self.all_trails = all_trails
        #self.trail_summary = trail_summary
        self.reference_list = [] #reference_list
        self.reference_lookup = {} #reference_lookup

    def _preprocess_tokens(self, tokens, add_ending=True):
        if add_ending:
            return [t.lower() for t in tokens if t.lower() not in self.stopwords] + [self.eol_symbol]
        else:
            return [t.lower() for t in tokens if t.lower() not in self.stopwords]

    def get_token_counts(self):

        token_counts = {}
        for t in self.token_list:
            if t == "ROOTNODE":
                continue
            if t == "$":
                continue
            if t in token_counts:
                token_counts[t] += 1
            else:
                token_counts[t] = 1
        return token_counts


    def _get_leaves(self, branch):

        nodes = [branch]
        leaves = set()
        while len(nodes) > 0:
            this_node = nodes.pop()
            if this_node.is_leaf:
                for ch in this_node.children:
                    leaves.add(ch)
            else:
                for ch in this_node.children:
                    nodes.append(ch)
        return list(leaves)

    def _collapse_ngrams(self, ngrams, min_count=1):

        sorted_ngrams = sorted([[ng[0], len(ng[0]), ng[1], ng[1]] for ng in ngrams], key=itemgetter(1), reverse=True)

        i = 0
        j = 1

        while i < len(sorted_ngrams)-1:
            #print(i,j,len(sorted_ngrams))
            i_ngram = sorted_ngrams[i]
            j_ngram = sorted_ngrams[j]
            if j_ngram[1] == i_ngram[1]: # same length
                j = j
            elif j_ngram[1] < i_ngram[1]-1: # more than 1 difference, skip to next i
                i += 1
                j = i
            else:
                i_text = i_ngram[0]
                j_text = j_ngram[0]
                matched = True
                offset = 0
                while matched and offset < len(j_text):
                    if i_text[offset+1] == j_text[offset]:
                        offset += 1
                        continue
                    else:
                        matched = False
                if not matched:
                    matched = True
                    offset = 0
                    while matched and offset < len(j_text):
                        if i_text[offset] == j_text[offset]:
                            offset += 1
                            continue
                        else:
                            matched = False
                if matched:
                    if i_ngram[0][0] == 'National' and i_ngram[0][1] == 'Health':
                        j_ngram[3] -= i_ngram[2]   # update length of j ngram by subtracting longer string
                    else:
                        j_ngram[3] -= i_ngram[2]   # update length of j ngram by subtracting longer string
                    #break
                    #i += 1
                    #j = i +1
                    #continue
                #else:
                #    j = j
            if j >= len(sorted_ngrams)-1:
                i += 1
                j = i + 1
            else:
                j += 1

        return([[ng[0],ng[3]] for ng in sorted_ngrams if ng[3] >= min_count])


    def _get_ngrams(self, min_count=1, min_length=1):

        ngrams = []
        branches = [[ch, []] for ch in self.tree.children]
        while len(branches) > 0:
            this_branch = branches.pop()
            branch = this_branch[0]
            text = this_branch[1]
            size = branch.get_branch_size()
            if size < min_count:
                continue
            this_text = self.token_list[branch.position:branch.position+branch.length]
            for i in range(len(this_text)):
                new_text = text + this_text[:i+1]
                if new_text[-1] != self.eol_symbol and len(new_text) >= min_length:
                    ngrams.append([new_text, size])
            if not branch.is_leaf:
                for ch in branch.children:
                    branches.append([ch, new_text])
        return ngrams

    def search_tokens(self, *tokens_list):

        match_list = set()
        #print(tokens_list)
        for tokens in tokens_list:
            tokens = self._preprocess_tokens(tokens, add_ending=False)
            match = self._search_suffix(tokens)
            match_count = sum([x[1] for x in match])
            match_path = [x[0] for x in match]
            branch = self._get_branch(match_path)
            debugprint("Searched",tokens,"Matched",match_count,"of",len(tokens),"Matches:",match,"Branch",branch)
            if match_count == len(tokens):
                #self.printtree(branch)
                leaves = self._get_leaves(branch)
                for l in leaves:
                    ref = self.get_ngram_reference(l)
                    match_list.add(ref)
                debugprint("Leaves:", leaves)
        return list(match_list)


    def add_tokens(self, tokens, reference = None):
        
        token_list = self._preprocess_tokens(tokens)

        if len(token_list) == 1:
            return
        for tok in token_list:
            self.token_list.append(tok)
        start_pos = len(self.token_list) - len(token_list)
        self.reference_list.append(start_pos)
        self.reference_lookup[start_pos] = [start_pos, len(token_list), reference]
        for i in range(len(token_list)-1):
            token_suffix = token_list[i:]
            debugprint("New suffix:",token_suffix)
            match = self._search_suffix(token_suffix)
            match_count = sum([x[1] for x in match])
            if match_count == 0:
                self.tree.add_child(start_pos+i, length=len(token_suffix))
                self.tree.children[-1].children.append(start_pos)
            else:
                match_path = [x[0] for x in match]
                last_stop = match[-1]
                last_count = last_stop[1]
                branch = self._get_branch(match_path)
                if match_count == len(token_suffix): # and last_count == branch.length:
                    debugprint("\tFull match")
                    if not branch.is_leaf:
                        print("Full match not a leaf!")
                    branch.children.append(start_pos)
                else:
                    debugprint("\tPartial match", match_count,"of",len(token_suffix),"path",match_path)
                    debugprint("\tMatch:",match)
                    route_count = match_count - last_count
                    if branch.length == last_stop:
                        debugprint("\tAll branch matched")
                        #branch.children.append(SuffixTree(start_pos+i+route_count, length=last_count))
                        branch.add_child(start_pos+i+route_count, length=last_count)
                        branch.children[-1].children.append(start_pos)
                    else:
                        debugprint("\tSplitting",
                                self.token_list[branch.position:branch.position+last_count],
                                "pos", branch.position,
                                "len",branch.length,"last",last_stop,
                                "last count", last_count,
                                "start pos", start_pos,
                                "i", i,
                                "route count", route_count,
                                "match count", match_count)
                        if branch.length-last_count > 0:
                            #branch.children.append(SuffixTree(branch.position+last_count,
                            #                                  length=branch.length-last_count))
                            debugprint("Branch is a leaf?",branch.is_leaf)
                            debugprint("Branch children are",branch.children)
                            current_children = branch.children
                            branch.children = []
                            branch.add_child(branch.position+last_count, length=branch.length-last_count, is_leaf=branch.is_leaf)
                            debugprint("Branch children are now",branch.children)
                            branch.children[-1].children = current_children
                            debugprint("Its children are now",[c.children for c in branch.children])
                            #if not branch.is_leaf:
                            #    print("Its children are now",[c.children.set_leaf(branch.is_leaf) for c in branch.children])
                            #branch.children[-1].children.append(start_pos)
                            branch.is_leaf = False
                            branch.length = last_count
                        #branch.children.append(SuffixTree(start_pos+i+match_count,
                        #                                  length=len(token_suffix)-match_count))
                        branch.add_child(start_pos+i+match_count, length=len(token_suffix)-match_count)
                        branch.children[-1].children.append(start_pos)

    def _search_suffix(self, tokens, preprocess=False):

        if preprocess:
            token_list = self._preprocess_tokens(tokens)
        else:
            token_list = [t for t in tokens]
        this_tree = self.tree
        token_matches = []
        offset = -1
        if token_list[0] in self.token_lookup:
            self.lookup_count += 1
            token_id = self.token_lookup[token_list[0]]
            tree_list = [(token_id, self.tree.children[token_id])]
        else:
            tree_list = [(i,c) for i,c in enumerate(self.tree.children)]
            self.token_lookup[token_list[0]] = len(self.tree.children)
            return []
        suffix_found = True
        keep_searching = True
        while len(token_list) > 0 and keep_searching:
            this_token = token_list.pop(0)
            token_match = False
            while len(tree_list) > 0 and not token_match:
                this_tree = tree_list.pop(0)
                offset = -1
                tree_num = this_tree[0]
                this_tree = this_tree[1]
                while offset < this_tree.length:
                    offset += 1
                    tree_token = self.token_list[this_tree.position+offset]
                    if tree_token == this_token:
                        token_match = True
                        tree_list = []
                        if len(token_list) > 0 and offset < this_tree.length-1:
                            this_token = token_list.pop(0)
                        else:
                            break
                    else:
                        token_match = False
                        break
                if token_match:
                    token_matches.append([tree_num,offset+1])
                    if not this_tree.is_leaf:
                        tree_list = [(i,ch) for i,ch in enumerate(this_tree.children)]
                    offset = -1
                else:
                    if offset > 0:
                        token_matches.append([tree_num, offset])
            if not token_match:
                keep_searching = False

        return token_matches


    def __str__(self):
        return self.token_list[self.position:self.position+self.length]

    def __repr__(self):
        return " ".join(self.token_list[self.position:self.position+self.length])

    def _get_branch(self, path):
        
        this_branch = self.tree
        for p in path:
            this_branch = this_branch.children[p]
        return this_branch

    def printtree(self, tree, limit=20):
        
        print("*******Begin Tree***********")
        nodes = [[tree, 0]]
        while len(nodes) > 0:
            n = nodes.pop()
            print("Pos",n[0].position,n[0].length,len(n[0].children))
            tokens =  self.token_list[n[0].position:n[0].position+n[0].length]
            if n[0].is_leaf:
                add_text = "(Leaf) " + ",".join([str(x) for x in n[0].children])
            else:
                add_text = ""
            print("\t" * n[1], tokens, add_text)
            children = random.sample(n[0].children, min(limit, len(n[0].children)))
            if not n[0].is_leaf:
                for ch in children:
                    nodes.append([ch, len(tokens)+n[1]])
        print("*******End Tree***********")


    def get_reference_list(self):
        return self.reference_list

    def get_reference_lookup(self):
        return self.reference_lookup

    #def _filter_trails(self, min_matches, min_length, max_length=1000):

    #    summary = []
    #    for k1,v1 in self.trail_summary.items():
    #        for k2,v2 in v1.items():
    #            if len(v2) < min_matches or (k2 < min_length or k2 > max_length):
    #                if k2 > 2:
    #                    debugprint("\tskipping",k1,k2,len(v2))
    #                continue
    #            tokens = [self.token_list[x] for x in range(k1,k1+max(k2,1))]
    #            if tokens[-1] == "$":
    #                tokens = tokens[:-1]
    #            summary.append([tokens, len(v2), k1, max(k2,1),  v2])
#
#        return summary

#    def _collapse_trail(self, trail, min_matches):
#        C_FLD = 1  # Match count field
#        L_FLD = 3  # Token length field
#        P_FLD = 2  # Position field
#        M_FLD = 4  # Match list field
#
#        trail.sort(key=itemgetter(L_FLD), reverse=True)
#        process = True
#        i = 0
#        j = 1
#        i_back = 0
#        new_trail = []
#        i_inserted = False
#        inserts = dict()
#
#        while process:
#            if i >= len(trail):
#                process = False
#                continue
#            if j >= len(trail):
#                if i not in inserts:
#                    new_trail.append(trail[i])
#                    inserts[i] = len(new_trail)-1
#                i += 1
#                j = i+1
#                continue
#            start_i = trail[i][P_FLD]
#            end_i = sum(trail[i][P_FLD:P_FLD+2])-1
#            start_j = trail[j][P_FLD]
#            end_j = sum(trail[j][P_FLD:P_FLD+2])-1
#            if trail[i][L_FLD] == trail[j][L_FLD]:
#                j += 1
#                continue
#            if trail[i][L_FLD] - trail[j][L_FLD] > 1:
#                if i not in inserts:
#                    new_trail.append(trail[i])
#                    inserts[i] = len(new_trail)-1
#                i += 1
#                j = i+1
#                continue
#
#            if self.token_list[start_i] == self.token_list[start_j]:
#                #print("**************gotta left match***************", start_i, start_j, ST.token_list[start_j])
#                #print("\t",topN[i])
#                #print("\t",topN[j])
#                matched = True
#                offset = 1
#                while offset < trail[j][L_FLD]:
#                    #print("\t",ST.token_list[start_i+offset], ST.token_list[start_j+offset])
#                    if self.token_list[start_i+offset] == self.token_list[start_j+offset]:
#                        offset += 1
#                        continue
#                    matched = False
#                    break
#                if matched:
#                    #print("\tLeft match")
#                    #print("\t",topN[i])
#                    #print("\t",topN[j])
#                    if j in inserts:
#                        updated_j = new_trail[inserts[j]]
#                    else:
#                        updated_j = [trail[j][0], 0, -1, -1, trail[j][M_FLD]]
#                    updated_matches = updated_j[M_FLD].difference([x for x in trail[i][M_FLD]])
#                    #print("\tAfter",updated_matches)
#                    #if len(updated_matches) >= THRESHOLD:
#                    updated_j[C_FLD] = len(updated_matches)
#                    updated_j[P_FLD] = trail[j][P_FLD]
#                    updated_j[L_FLD] = trail[j][L_FLD]
#                    updated_j[M_FLD] = updated_matches
#                    if j in inserts:
#                        #print("\tUpdated",j,len(updated_matches),updated_j)
#                        new_trail[inserts[j]] = updated_j
#                    else:
#                        #print("\tInserted",j,len(updated_matches),updated_j)
#                        new_trail.append(updated_j)
#                        inserts[j] = len(new_trail)-1
#
#                j += 1
#                continue
#
#            elif self.token_list[end_i] == self.token_list[end_j]:
#                #print("**************gotta right match***************", end_i, end_j, self.token_list[end_i])
#                #print("\t",topN[i])
#                #print("\t",topN[j])
#                matched = True
#                offset = 1
#                while offset < trail[j][L_FLD]:
#                    #print("\t",ST.token_list[end_i-offset], ST.token_list[end_j-offset])
#                    if self.token_list[end_i-offset] == self.token_list[end_j-offset]:
#                        offset += 1
#                        continue
#                    matched = False
#                    break
#                if matched:
#                    #print("Right match")
#                    #print("\t",topN[i])
#                    #print("\t",topN[j])
#                    if j in inserts:
#                        updated_j = new_trail[inserts[j]]
#                    else:
#                        updated_j = [trail[j][0], 0, -1, -1, trail[j][M_FLD]]
#                    updated_matches = updated_j[M_FLD].difference([x for x in trail[i][M_FLD]])
#                    #print("\tAfter",updated_matches)
#                    #if len(updated_matches) >= THRESHOLD:
#                    updated_j[C_FLD] = len(updated_matches)
#                    updated_j[P_FLD] = trail[j][P_FLD]
#                    updated_j[L_FLD] = trail[j][L_FLD]
#                    updated_j[M_FLD] = updated_matches
#                    if j in inserts:
#                        #print("\tInserted",j,len(updated_matches),updated_j)
#                        new_trail[inserts[j]] = updated_j
#                    else:
#                        #print("\tUpdated",j,len(updated_matches),updated_j)
#                        new_trail.append(updated_j)
#                        inserts[j] = len(new_trail)-1
#    
#                j += 1
#                continue
#    
#            j += 1
#
#        return [t for t in new_trail if t[1] >= min_matches]
#
    def get_phrases(self, min_count, min_length, max_length):

        ngrams = self._get_ngrams(min_count, min_length)
        return self._collapse_ngrams(ngrams, min_count)

    def _closest_below(self, myList, myNumber):
        pos = bisect_left(myList, myNumber)
        if pos == 0:
            return myList[0]
        if pos == len(myList):
            return myList[-1]
        before = myList[pos - 1]
        after = myList[pos]
        if myNumber >= after:
            return after
        else:
            return before

    def get_ngram_reference(self, position):

        closest = self._closest_below(self.get_reference_list(), position)
        return self.get_reference_lookup()[closest][2]

    def __str__(self):
        #return str(self.this_position)
        return self.token_list[self.position]

if __name__ == "__main__":

    ST = SuffixTree()

    strings = ['Tackling Drugs Changing Lives',
               'Tackling Drugs to Build a Better Britain',
               'Tackling Bovine TB Blog',
               'Crown Court Rule Committee',
               'Crown Estate',
               'Crown Prosecution Service',
               'Crown Prosecution Service Inspectorate',
               'Crown Prosecution Service',
               'Crown Commercial Service',
               'London 2012',
               'London 2012',
               'My London 2012 Mascots',
               'Fit for London 2012',
               'Olympic Legacy Speech 5th July 2012']
    #strings = ['London 2012',
    #           'London 2012 Olympics',
    #           'Visit London']
    #strings = ['Crown',
    #           'Crown Prosecution Service',
    #           'Crown Prosecution Service Inspectorate',
    #           'Crown']

    counter = 0
    for s in strings:
        counter += 1
        ST.add_tokens(s.split(" "), 'E' + str(counter))
    ST.printtree(ST.tree)
    print(ST.token_list)
    print(ST.tree.get_tree_size())
    print(ST.tree.get_branch_size())
    print(ST.get_phrases(2,2,4))
    print(ST.tree.children)
    print(ST.token_lookup)
    #print(sf.trail_summary)
    #ST.search_tokens(['Bovine'])
    #ST.search_tokens(['Crown','Estate'])
    #ST.search_tokens(['Crown','Prosecution'])
    #ST.search_tokens(['Crown','Prosecution','Service'])
    #ST.search_tokens(['Crown','Prosecution','News'])
    #ST.search_tokens(['Coffee'])
    #ST.search_tokens(['London','2012'])
    exit()


def text_to_parts(text):
    parts = []
    this_text = ""
    part_type = "default"
    new_part_type = part_type
    prev = ""
    save = False
    start = 0
    for i,c in enumerate(text):
        if c == "(":
            new_part_type = "bracket"
            save = True
        elif c == ")":
            new_part_type = "default"
            save = True
        elif c in ["-", "–"] and prev == " ":
            new_part_type = "hyphen"
            save = True
        else:
            this_text += c

        if i == len(text)-1:
            save = True
        if save:
            this_text = this_text.strip()
            if len(this_text) > 0:
                if "http" in this_text:
                    p_category = "web"
                else:
                    p_category = "default"
                if this_text.upper() == this_text: # needs fixing for format A{2-9} but sort of works as is
                    p_category = "caps"

                parts.append([this_text, part_type, start, p_category])
            start = i+1
            part_type = new_part_type
            this_text = ""
            save = False
        prev = c
    return parts

