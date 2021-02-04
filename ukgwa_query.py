from ukgwa_view import UKGWAView

class QueryEngine:

    def __init__(self):

        self.selections = {}
        self.views = {}

    def add_view(self, identifier, view):
        self.views[identifier] = view

    def filter_view(self, identifier, *args):
        view = self.views[identifier]
        for idx in view._filter(*args):
            yield idx
            #if view.comparison(idx, *args):
            #    yield idx

    def exclude(self, identifier):
        self._set_select(identifier, False, override = True)

    def include(self, identifier):
        self._set_select(identifier, True)

    def update(self, identifier, value):
        self._set_select(identifier, value, override = True)

    def _set_select(self, identifier, select_value, override = False):

        if not override:
            if identifier in self.selections:
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
        while not self.selections[next_item]:
            next_item = next(self.select_iter)
        return next_item

if __name__ == '__main__':
    Q = QueryEngine()
    for i in range(20):
        Q.update(i, i % 3 == 0)
    print(Q.selections)
    print(Q.selections[3])
    Q.exclude(3)
    print(Q.selections[3])
    Q.include(3)
    print(Q.selections[3])
    Q.update(3, True)
    print(Q.selections[3])
