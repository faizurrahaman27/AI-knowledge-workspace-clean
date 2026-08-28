from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 1,
) -> List[str]:
    """
    Paragraph-aware chunking.

    Keeps paragraphs intact and overlaps using
    whole paragraphs instead of raw characters.
    """

    paragraphs = [
        p.strip()
        for p in text.split("\n\n")
        if p.strip()
    ]

    if not paragraphs:
        return []

    chunks = []

    current_chunk = []

    current_length = 0

    for paragraph in paragraphs:

        paragraph_length = len(paragraph)

        if (
            current_length + paragraph_length
            <= chunk_size
        ):

            current_chunk.append(paragraph)

            current_length += paragraph_length

        else:

            chunks.append("\n\n".join(current_chunk))

            overlap = current_chunk[-chunk_overlap:] if current_chunk else []

            current_chunk = overlap + [paragraph]

            current_length = sum(len(p) for p in current_chunk)

    if current_chunk:

        chunks.append("\n\n".join(current_chunk))

    return chunks

