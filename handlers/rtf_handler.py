from htmldocx import HtmlToDocx
from docx import Document
from io import BytesIO


class HTMLDocument:
    """Utility for building simple HTML documents.

    The class stores a list of HTML fragments that can be exported as a full
    HTML document, converted to DOCX, or copied to the system clipboard using
    the Windows CF_HTML format.
    """

    def __init__(self):
        # Store document body fragments in order.
        self.content = []

    def add_content(self, text, tag=None, newline=True):
        """Append text wrapped in an optional HTML tag.

        Args:
            text: Text to append.
            tag: Optional tag name (e.g. "h1", "p").
            newline: If true, append a ``<br>`` after the text.
        """

        if tag:
            self.content.append(f"<{tag}>{text}</{tag}>")
        else:
            self.content.append(str(text))
        if newline:
            self.content.append("<br>")

    def add_bullet(self, text):
        """Append a bullet list item to the document."""

        self.content.append(f"<ul><li>{text}</li></ul>")

    # ------------------------------------------------------------------
    # HTML helpers
    # ------------------------------------------------------------------
    def _build_fragment(self):
        """Return the inner HTML fragment without any wrapping tags."""

        return "".join(self.content)

    def get_html(self):
        """Return the full HTML document without clipboard headers."""

        body = self._build_fragment()
        return f"<html><body>{body}</body></html>"

    # ------------------------------------------------------------------
    # DOCX export helpers
    # ------------------------------------------------------------------
    def create_docx(self):
        """Convert the HTML content to a Word ``Document`` instance."""

        html_content = self.get_html()
        document = Document()
        converter = HtmlToDocx()
        converter.add_html_to_document(html_content, document)
        return document

    def get_doc(self):
        """Return the DOCX as an in-memory ``BytesIO`` stream."""

        document = self.create_docx()
        file_stream = BytesIO()
        document.save(file_stream)
        file_stream.seek(0)
        return file_stream

    def save_doc(self, filename="output.docx"):
        """Save the DOCX to disk and return ``filename``."""

        document = self.create_docx()
        document.save(filename)
        return filename
