# Generic class for others to inherit methods from

import operator

class UKGWAView:

    def __init__(self):

        self.index = {}
        self.fields = {}

    def _get_truth(index_value, relation, value):
        ops = {'>': operator.gt,
               '<': operator.lt,
               '>=': operator.ge,
               '<=': operator.le,
               '=': operator.eq,
               '<>': operator.ne,
               'in': operator.contains}
        if relation == 'in':
            return ops[relation](value, index_value)
        else:
            return ops[relation](index_value, value)

    def comparison(self, key, field, operator, value):

        if key not in self.index:
            return False
        field_val = self.index[key][self.fields[field]]
        return UKGWAView._get_truth(field_val, operator, value)

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

    V = UKGWAView()
    V.fields = {'A':0, 'B':1}
    V.add_entry('ABC', [1,2])
    V.add_entry('DEF', [3,4])
    print(V.index)
    print(V.comparison('DEF','B','<',6))
    V.update_field('DEF', 'B', 8)
    print(V.index)
    print(V.comparison('DEF','B','<',6))
    print(V.get_field('DEF','B'))
    print(V.comparison('DEF','B','in',[3,6,7]))
    print(V.comparison('DEF','B','<>',6))
