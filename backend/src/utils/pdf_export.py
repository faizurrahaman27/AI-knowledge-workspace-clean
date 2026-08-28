"""
Renders generated study content (summary/mindmap/flashcards/quiz text) to
a downloadable PDF. Deliberately simple: strips Markdown syntax down to
readable plain text with basic heading/bullet formatting rather than a
full Markdown-to-PDF renderer -- good enough for "here's your study pack
as a PDF," not a typesetting engine.
"""

import io
import re

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT


def _clean_line(line: str) -> str:
    # Escape XML-sensitive chars for reportlab's mini-HTML markup, then
    # translate a few common Markdown tokens to <b>/<i>.
    line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
    line = re.sub(r"\*(.+?)\*", r"<i>\1</i>", line)
    return line


def build_study_pack_pdf(document_title: str, sections: list[tuple[str, str]]) -> bytes:
    """
    sections: list of (heading, markdown_text) tuples, rendered in order.
    Returns raw PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], alignment=TA_LEFT)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=8)
    body_style = ParagraphStyle("BodyX", parent=styles["BodyText"], spaceAfter=6, leading=15)
    bullet_style = ParagraphStyle("BulletX", parent=body_style, leftIndent=16, bulletIndent=4)

    story = [Paragraph(_clean_line(document_title), title_style), Spacer(1, 0.2 * inch)]

    for i, (heading, text) in enumerate(sections):
        if i > 0:
            story.append(PageBreak())
        story.append(Paragraph(_clean_line(heading), h2_style))

        for raw_line in (text or "").split("\n"):
            line = raw_line.strip()
            if not line:
                story.append(Spacer(1, 0.08 * inch))
                continue

            if line.startswith("#"):
                line = line.lstrip("#").strip()
                story.append(Paragraph(_clean_line(line), h2_style))
            elif line.startswith(("-", "*", "•")):
                story.append(Paragraph("• " + _clean_line(line[1:].strip()), bullet_style))
            else:
                story.append(Paragraph(_clean_line(line), body_style))

    doc.build(story)
    return buffer.getvalue()
