from ukgwa_view import UKGWAView
from ukgwa_query import QueryEngine
from text_utils import SuffixTree

class UKGWATextIndex(UKGWAView):

    def __init__(self, stop_words = set(), eol_symbol = '$'):

        super().__init__()
        # self.add_entry(reference, [reference, link.text.replace("\n"," ").strip(), category, href, 'N'])
        self.eol_symbol = eol_symbol  # Character to add to end of tokens for suffix array (otherwise it doesn't work)
        #self.fields['REF'] = 0   # Not sure what fields there need to be yet; default field of NGRAM for consistency with API?

        self.index = SuffixTree(stop_words, eol_symbol)
        self.stop_words = stop_words

    def add_tokens(self, tokens, reference):

        self.index.add_tokens(tokens, reference)

    def _filter(self, field, operator, *value):

        search_matches = self.index.search_tokens(*value)
        for m in search_matches:
            yield m

    def comparison(self, key, field, operator, value):
        return False

    def get_phrases(self, min_count, min_length, max_length=10):
        return self.index.get_phrases(min_count, min_length, max_length)
