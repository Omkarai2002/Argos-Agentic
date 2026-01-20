
from logging import getLogger
logger = getLogger(__name__)

class SuggestionRouter:
    def __init__(self, word_engine, spell_engine, ngram_engine):
        self.word_engine = word_engine
        self.spell_engine = spell_engine
        self.ngram_engine = ngram_engine

    def suggest(self, text_state):
        if text_state.inside_word:
            return {
                "completion": self.word_engine.complete(text_state.current_word),
                "misspelled": self.spell_engine.is_misspelled(text_state.current_word),
                "suggestions": []
            }

        if text_state.previous_word:
            last_word = text_state.previous_word[-1]
            logger.info(f"last_word: {last_word}")
            logger.info(f"suggestions: {self.ngram_engine.predict_next(last_word)}")
            if self.ngram_engine.predict_next(last_word):

                return {
                    "completion": [],
                    "misspelled": False,
                    "suggestions": self.ngram_engine.predict_next(last_word)
                }
            else:
                logger.info("No suggestions found from ngram engine.")
                #this code is reserved for future use of SNN model.
                return {
                    "completion": [],
                    "misspelled": False,
                    "suggestions": []
                }

        return {
            "completion": [],
            "misspelled": False,
            "suggestions": []
        }
