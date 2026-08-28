class SentenceTransformer:
    def __init__(self, *a, **k): pass
    def encode(self, chunks):
        import numpy as np
        class Arr(list):
            def tolist(self): return [[0.0]*8 for _ in chunks]
        return Arr()

class CrossEncoder:
    def __init__(self, *a, **k): pass
    def predict(self, pairs):
        return [0.5] * len(pairs)
