import fitz


def extract_pages_from_pdf(file_path: str):
    """
    Extract text page by page.

    Returns:
    [
        {
            "page": 1,
            "text": "..."
        },
        {
            "page": 2,
            "text": "..."
        }
    ]
    """

    document = fitz.open(file_path)

    pages = []

    for index, page in enumerate(document):

        text = page.get_text().strip()

        if text:

            pages.append(
                {
                    "page": index + 1,
                    "text": text,
                }
            )

    document.close()

    return pages