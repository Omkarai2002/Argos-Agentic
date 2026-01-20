import pickle
import os
from collections import defaultdict
from nltk.corpus import brown
import logging
logger = logging.getLogger(__name__)

class GramBuilder:
    CACHE_FILE = "bigram.pkl"

    def __init__(self, top_k=1):
        self.bigram_model = None
        self.top_next = None
        self.top_k = top_k

        if os.path.exists(self.CACHE_FILE):
            logger.warning("Loading cached bigram model...")
            self._load_cache()
        else:
            logger.warning("Cache not found. Building bigram model from corpus...")
            self._build()
            self._save_cache()

    def _is_word(self, w):
        return any(c.isalnum() for c in w)

    def _build(self):
        self.bigram_model = defaultdict(lambda: defaultdict(int))

        for sentence in brown.sents():
            words = [w.lower() for w in sentence if self._is_word(w)]
            for w1, w2 in zip(words, words[1:]):
                self.bigram_model[w1][w2] += 1

        # Precompute top-k next words
        self.top_next = {}
        for w1, nexts in self.bigram_model.items():
            self.top_next[w1] = sorted(nexts, key=nexts.get, reverse=True)[:self.top_k]

        logger.info("Bigram model built.")

    def _convert_to_dict(self):
        # Convert nested defaultdicts to normal dicts for pickling
        return {w1: dict(nexts) for w1, nexts in self.bigram_model.items()}

    def _save_cache(self):
        temp_file = self.CACHE_FILE + ".tmp"
        with open(temp_file, "wb") as f:
            pickle.dump((self._convert_to_dict(), self.top_next), f)
        os.replace(temp_file, self.CACHE_FILE)
        logger.info(f"Bigram model cached to {self.CACHE_FILE}")

    def _load_cache(self):
        try:
            with open(self.CACHE_FILE, "rb") as f:
                self.bigram_model, self.top_next = pickle.load(f)
            logger.info("Cache loaded successfully.")
        except (EOFError, pickle.UnpicklingError):
            logger.error("Cache broken or empty. Rebuilding model...")
            self._build()
            self._save_cache()


    def predict_next(self, word: str):
        if self.top_next is None:
            raise ValueError("Model not built or loaded.")
        return self.top_next.get(word.lower(), [])[:self.top_k]


# ---------------- Test ----------------
if __name__ == "__main__":
    
    builder = GramBuilder(top_k=1)
    
    print("Next words prediction:", builder.predict_next("good"))

