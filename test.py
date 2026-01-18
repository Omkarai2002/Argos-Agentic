from suggestion_layer.text_state.extractor import TextState

ts = TextState("google ", 7)

print(ts.current_word)      # sci
print(ts.previous_word)    # ['general']
print(ts.inside_word)       # True
