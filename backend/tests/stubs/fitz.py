def open(path):
    class DummyDoc:
        def __iter__(self): return iter([])
        def close(self): pass
    return DummyDoc()
