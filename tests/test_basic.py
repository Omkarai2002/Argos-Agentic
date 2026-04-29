import sys
import os

sys.path.append(os.path.abspath("."))

def test_import():
    import sockets.client
    assert True