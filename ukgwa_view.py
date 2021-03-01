# Generic class for others to inherit methods from

import operator

class UKGWAOperator:

    def __init__(self):
        None

    def eq(self, A, B):
        return operator.eq(A,B)

    def lt(self, A, B):
        return operator.lt(A,B)

    def gt(self, A, B):
        return operator.gt(A,B)

    def le(self, A, B):
        return operator.le(A,B)

    def ge(self, A, B):
        return operator.ge(A,B)

    def ne(self, A, B):
        return operator.ne(A,B)

    def contains(self, A, B):
        return operator.contains(A,B)

    def isprefix(self, A, B):
        if len(B) < len(A):
            return False
        i = 0
        while i < len(A):
            if A[i] != B[i]:
                return False
            i += 1
        return True


class UKGWAView:

    def __init__(self):

        self.index = {}
        self.fields = {}
        self.operator = UKGWAOperator()

    def _get_truth(self,index_value, relation, value):
        ops = {'>': self.operator.gt,
               '<': self.operator.lt,
               '>=': self.operator.ge,
               '<=': self.operator.le,
               '=': self.operator.eq,
               '<>': self.operator.ne,
               'in': self.operator.contains,
               'isprefix': self.operator.isprefix}
        if relation == 'in':
            return ops[relation](value, index_value)
        else:
            return ops[relation](index_value, value)

    def _filter(self, field, operator, value):
        for idx in self:
            if self.comparison(idx, field, operator, value):
                yield idx

    def comparison(self, key, field, operator, value):

        if key not in self.index:
            return False
        field_val = self.index[key][self.fields[field]]
        return self._get_truth(field_val, operator, value)

    def lookup(self, key, fields = []):

        field_index = [self.fields[f] for f in fields]
        if key in self.index:
            if len(fields) == 0:
                return self.index[key]
            return_val = [x for i,x in enumerate(self.index[key]) if i in field_index]
        else:
            return_val = []
        return return_val

    def get_field(self, key, field):

        if key in self.index:
            return self.index[key][self.fields[field]]
        return None

    def add_entry(self, key, values):

        self.index[key] = values

    def update_field(self, key, field, value):

        if key in self.index:
            self.index[key][self.fields[field]] = value

    def __iter__(self):
        return iter(self.index)


if __name__ == "__main__":

    OP = UKGWAOperator()
    print("T",OP.eq('a','a'))
    print("T",OP.contains('abc','ab'))
    print("F",OP.contains('ab','abc'))
    print("T",OP.isprefix('ab','abc'))
    print("F",OP.isprefix('abc','ab'))
    print("T",OP.isprefix(['abc','def','g','h'],['abc','def','g','h','i']))
    print("F",OP.isprefix(['abc','def','g','h'],['ab','def','g','h','i']))
    print("F",OP.isprefix(['abc','def','g','h'],['abc','def','g']))
    #V = UKGWAView()
    #V.fields = {'A':0, 'B':1}
    #V.add_entry('ABC', [1,2])
    #V.add_entry('DEF', [3,4])
    #print(V.index)
    #print(V.comparison('DEF','B','<',6))
    #V.update_field('DEF', 'B', 8)
    #print(V.index)
    #print(V.comparison('DEF','B','<',6))
    #print(V.get_field('DEF','B'))
    #print(V.comparison('DEF','B','in',[3,6,7]))
    #print(V.comparison('DEF','B','<>',6))
