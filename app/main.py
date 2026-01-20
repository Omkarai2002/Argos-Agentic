from suggestion_layer.text_state.extractor import TextState
from suggestion_layer.router import SuggestionRouter
from suggestion_layer.word_completion.engine import WordCompletionEngine
from suggestion_layer.spell_check.engine import SpellCheckEngine
from suggestion_layer.ngram.engine import NGramEngine
from logging_config import LoggerFeature
import logging

LoggerFeature.setup_logging()

logger = logging.getLogger(__name__)
logger.info("App started")

words = []
#sentences = ["general science", "good morning"]

router = SuggestionRouter(
    WordCompletionEngine(words),
    SpellCheckEngine(words),
    NGramEngine(top_k=1)
)

ts = TextState("good ", 5)
print(router.suggest(ts))
