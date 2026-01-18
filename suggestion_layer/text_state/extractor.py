class TextState:
    def __init__(self,text:str,cursor:int):
        self.text=text
        self.cursor=cursor
        self.current_word=""
        self.previous_word=[]
        self.inside_word=False
        self._extract()

    def _extract(self):
        left_text=self.text[:self.cursor]

        if not left_text or left_text.endswith(" "):
            self.inside_word=False
            self.previous_word=left_text.strip().split(" ")
            return
        self.inside_word=True
        parts=left_text.split(" ")
        self.current_word=parts[-1]
        self.previous_word=parts[:-1]