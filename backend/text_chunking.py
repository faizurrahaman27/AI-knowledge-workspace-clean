from src.utils.chunking import chunk_text

text = "A" * 1500

chunks = chunk_text(text)

print(len(chunks))

for i, chunk in enumerate(chunks):
    print(i, len(chunk))