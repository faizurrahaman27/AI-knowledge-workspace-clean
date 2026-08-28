These are NOT real dependencies -- they're minimal stand-ins for
sentence-transformers / chromadb / PyMuPDF / ollama so the test suite can
run in CI/offline without downloading multi-GB models. They're inserted
onto sys.path only for the test session (see conftest.py) and are never
part of the shipped application.
