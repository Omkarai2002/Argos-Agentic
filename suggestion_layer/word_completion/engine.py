from wordfreq import zipf_frequency,top_n_list

class WordCompletionEngine:
    def __init__(self, words: list[str]):
        # Keep words normalized
        self.words = sorted(set(w.lower() for w in words))

    def complete(self, prefix: str, limit: int = 5):
        if not prefix or len(prefix) < 2:
            return []

        prefix = prefix.lower()

        #Prefix match
        candidates = [w for w in top_n_list("en", 100000) if w.startswith(prefix)]

        if not candidates:
            return []

        # Rank by real-world frequency
        
        #print("Candidates:", candidates)
        #Return top results
        return candidates[0]
