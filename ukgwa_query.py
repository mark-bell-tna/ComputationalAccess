class QueryEngine:

    def __init__(self):

        self.selections = {}

    def set_select(self, identifier, select_value, override = False):

        if not override:
            if identifier in select_value:
                return
        self.selections[identifier] = select_value
        
    def get_select(self, identifier):

        if identifer not in self.selections:
            return False
        else:
            return self.selections[identifier]

    def clear(self):

        self.selections = {}

    def __iter__(self):
        self.select_iter = iter(self.selections)
        return self

    def __next__(self):

        next_item =  next(self.select_iter)
        if self.selections[next_item]:
            return next_item
        else:
            return next(self)

if __name__ == '__main__':
    Q = QueryEngine()
    for i in range(20):
        Q.set_select(i, i % 3 == 0)
    print(Q.selections)
    for s in Q:
        print(s)
