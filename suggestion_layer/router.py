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
            print("last_word:", last_word)
            print("suggestions:", self.ngram_engine.predict_next(last_word))
            return {
                "completion": [],
                "misspelled": False,
                "suggestions": self.ngram_engine.predict_next(last_word)
            }

        return {
            "completion": [],
            "misspelled": False,
            "suggestions": []
        }
