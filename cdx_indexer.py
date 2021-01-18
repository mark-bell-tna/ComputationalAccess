#!/usr/bin/python3

import urllib.request
from urllib.error import HTTPError
from cdx_reader import CDXReader
from ukgwa_view import UKGWAView

class TemporalIndexer(UKGWAView):

    def __init__(self):

        super().__init__()
        self.fields['MIN'] = 0
        self.fields['MAX'] = 1
        self.fields['COUNT'] = 2
        self.fields['CDX'] = 3

    def add_entry(self, url, identifier=None):

        if identifier is None:
            identifier = url
        this_cdx = CDXReader(url)
        this_cdx.read_cdx()
        super().add_entry(identifier, [this_cdx.min_snapshot, this_cdx.max_snapshot, this_cdx.snapshot_count, this_cdx])

    def comparison(self, identifier, *args):

        if args[2] == self.fields['CDX']:
            this_cdx = self.index[identifier][self.fields['CDX']]
            matched = False
            for snap in this_cdx:
                this_comparison = this_cdx.comparison(snap, args[3:])
                if this_comparison:
                    matched = True
                    break
            return matched
        else:
            return super().comparison(identifier, *args)

if __name__ == '__main__':
    T = TemporalIndexer()
    T.add_entry("www.hm-treasury.gov.uk/d/sanctionsconlist.txt","E1")
    T.add_entry("www.salt.gov.uk/industry_activity.html","E2")
    print(T.comparison("E1", "MIN", ">", 20000101000000))
    print(T.comparison("E2", "MIN", ">", 20000101000000))
    print(T.comparison("E1", "MAX", ">", 20120101000000))
    print(T.comparison("E1", "MAX", ">", 20220101000000))
    print(T.comparison("E2", "MAX", ">", 20120101000000))
    print(T.comparison("E2", "MAX", ">", 20080101000000))
