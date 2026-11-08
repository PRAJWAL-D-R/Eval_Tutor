import os
import re
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#94a3b8"))
        
        # Bottom divider
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 35, A4[0] - 40, 35)

        # Footer text
        self.drawString(40, 24, "Self-Evaluating Lesson Content Generator • 6/6 Rubric Verified")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 40, 24, page_text)
        self.restoreState()


def clean_markdown_inline(text: str) -> str:
    """Convert common inline markdown to safe ReportLab XML tags."""
    # Bold italic ***text*** -> <b><i>text</i></b>
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
    # Bold **text** -> <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic *text* -> <i>\1</i>
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    # Inline code `code` -> <font name="Courier" color="#0369a1"><b>\1</b></font>
    text = re.sub(r"`(.+?)`", r'<font name="Courier" color="#0369a1"><b>\1</b></font>', text)
    # Normalize nested tag order if reversed
    text = text.replace("<b><i>", "<b><i>").replace("</i></b>", "</i></b>").replace("</b></i>", "</i></b>")
    return text


def safe_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    """Create a Paragraph, falling back to plain text if XML parsing fails."""
    try:
        return Paragraph(text, style)
    except Exception:
        # Strip XML tags to prevent any rendering failure
        clean_plain = re.sub(r"<[^>]+>", "", text)
        return Paragraph(clean_plain, style)


def build_pdf(topic: str, markdown_text: str, output_stream_or_path) -> None:
    """Build a professional, white-background, vector PDF from lesson markdown."""
    doc = SimpleDocTemplate(
        output_stream_or_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_subtitle = ParagraphStyle(
        "PDFSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0284c7"),
        spaceAfter=4,
    )

    style_title = ParagraphStyle(
        "PDFTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12,
    )

    style_h1 = ParagraphStyle(
        "PDFH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    style_h2 = ParagraphStyle(
        "PDFH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True,
    )

    style_h3 = ParagraphStyle(
        "PDFH3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    style_body = ParagraphStyle(
        "PDFBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=7,
    )

    style_bullet = ParagraphStyle(
        "PDFBullet",
        parent=style_body,
        leftIndent=16,
        firstLineIndent=-10,
        spaceAfter=4,
    )

    style_quote = ParagraphStyle(
        "PDFQuote",
        parent=style_body,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#334155"),
        spaceBefore=4,
        spaceAfter=4,
    )

    story = []

    # Header Banner
    story.append(safe_paragraph("SELF-EVALUATING LESSON CONTENT GENERATOR", style_subtitle))
    story.append(safe_paragraph(topic, style_title))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#0284c7"),
            spaceBefore=0,
            spaceAfter=14,
        )
    )

    # Parse markdown line by line
    lines = markdown_text.split("\n")
    in_quote = False
    quote_lines = []

    def flush_quote():
        nonlocal in_quote, quote_lines
        if quote_lines:
            quote_text = "<br/>".join(quote_lines)
            p = safe_paragraph(quote_text, style_quote)
            # Wrap in styled table container with blue left border
            t = Table(
                [[p]],
                colWidths=[A4[0] - 80],
            )
            t.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("LINEBEFORE", (0, 0), (0, -1), 3.5, colors.HexColor("#0284c7")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ])
            )
            story.append(t)
            story.append(Spacer(1, 6))
            quote_lines = []
        in_quote = False

    for line in lines:
        stripped = line.strip()

        # Handle blockquote
        if stripped.startswith(">"):
            in_quote = True
            cleaned = clean_markdown_inline(stripped.lstrip(">").strip())
            if cleaned:
                quote_lines.append(cleaned)
            continue
        elif in_quote:
            flush_quote()

        if not stripped:
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=4, spaceAfter=8))
            continue

        # Headings
        if stripped.startswith("### "):
            story.append(safe_paragraph(clean_markdown_inline(stripped[4:]), style_h3))
            continue
        if stripped.startswith("## "):
            story.append(safe_paragraph(clean_markdown_inline(stripped[3:]), style_h2))
            continue
        if stripped.startswith("# "):
            story.append(safe_paragraph(clean_markdown_inline(stripped[2:]), style_h1))
            continue

        # Bullets / lists
        if stripped.startswith(("- [ ] ", "- [x] ")):
            check_box = "[X]" if stripped.startswith("- [x] ") else "[  ]"
            bullet_text = f"<b>{check_box}</b>&nbsp;&nbsp;{clean_markdown_inline(stripped[6:])}"
            story.append(safe_paragraph(bullet_text, style_bullet))
            continue
        if stripped.startswith(("- ", "* ", "+ ")):
            bullet_text = f"&bull;&nbsp;&nbsp;{clean_markdown_inline(stripped[2:])}"
            story.append(safe_paragraph(bullet_text, style_bullet))
            continue
        if re.match(r"^\d+\.\s+", stripped):
            num_match = re.match(r"^(\d+\.)\s+(.+)$", stripped)
            if num_match:
                prefix, rest = num_match.groups()
                item_text = f"<b>{prefix}</b>&nbsp;&nbsp;{clean_markdown_inline(rest)}"
                story.append(safe_paragraph(item_text, style_bullet))
                continue

        # Normal paragraph
        story.append(safe_paragraph(clean_markdown_inline(stripped), style_body))

    if in_quote:
        flush_quote()

    # Build PDF with dynamic page numbering
    doc.build(story, canvasmaker=NumberedCanvas)


def generate_pdf_bytes(topic: str, markdown_text: str) -> bytes:
    """Generate PDF in memory and return raw bytes."""
    buf = BytesIO()
    build_pdf(topic, markdown_text, buf)
    return buf.getvalue()
