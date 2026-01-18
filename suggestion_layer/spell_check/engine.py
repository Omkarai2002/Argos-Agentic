class SpellCheckEngine:
    def __init__(self,words:list[str]):
        self.dictionary=set(words)
        
    def is_misspelled(self, word:str)->bool:
        if len(word)<=2:
            return False
        return word not in self.dictionary