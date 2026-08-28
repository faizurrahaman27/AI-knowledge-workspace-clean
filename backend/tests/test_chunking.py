from src.utils.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_single_chunk():
    text = "This is one short paragraph."
    chunks = chunk_text(text, chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_splits_into_multiple_chunks():
    paragraphs = [f"Paragraph number {i} with some filler content." for i in range(50)]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, chunk_size=200)
    assert len(chunks) > 1

    # Every paragraph's content should still be present somewhere.
    joined = " ".join(chunks)
    for p in paragraphs:
        assert p in joined
