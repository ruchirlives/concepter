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

    def get_cf_html(self):
        """Return content formatted using the Windows CF_HTML specification."""

        fragment = self._build_fragment()
        html = f"<html><body><!--StartFragment-->{fragment}<!--EndFragment--></body></html>"

        header = (
            "Version:0.9\r\n"
            "StartHTML:00000000\r\n"
            "EndHTML:00000000\r\n"
            "StartFragment:00000000\r\n"
            "EndFragment:00000000\r\n"
        )

        start_html = len(header)
        start_fragment = html.find("<!--StartFragment-->") + len("<!--StartFragment-->")
        end_fragment = html.find("<!--EndFragment-->")
        start_fragment += start_html
        end_fragment += start_html
        end_html = start_html + len(html)

        header = header.replace("StartHTML:00000000", f"StartHTML:{start_html:08d}")
        header = header.replace("EndHTML:00000000", f"EndHTML:{end_html:08d}")
        header = header.replace("StartFragment:00000000", f"StartFragment:{start_fragment:08d}")
        header = header.replace("EndFragment:00000000", f"EndFragment:{end_fragment:08d}")

        return header + html

    # ------------------------------------------------------------------
    # Clipboard operations
    # ------------------------------------------------------------------
    def copy_to_clipboard(self):
        """Copy the document to the clipboard using CF_HTML when possible."""

        html = self.get_cf_html()

        import platform

        system = platform.system()
        if system == "Windows":
            try:
                import win32clipboard

                cf_html = win32clipboard.RegisterClipboardFormat("HTML Format")
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(cf_html, html.encode("utf-8"))
                finally:
                    win32clipboard.CloseClipboard()
            except Exception as exc:  # pragma: no cover - best effort only
                print(f"Failed to copy HTML to clipboard: {exc}")
        else:  # Non-Windows platforms fall back to plain text copy
            try:
                import pyperclip

                pyperclip.copy(html)
            except Exception as exc:  # pragma: no cover
                print(f"Failed to copy HTML to clipboard: {exc}")

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

    # ------------------------------------------------------------------
    # Legacy helpers retained for backwards compatibility
    # ------------------------------------------------------------------
    def get_simple_rtf(self):
        """Generate a basic RTF representation of the document.

        This is retained for compatibility but does not support rich HTML
        features. Use :meth:`get_cf_html` for richer clipboard export.
        """

        def html_to_rtf(html):
            import re

            rtf = html
            rtf = re.sub(r"<h1>(.*?)</h1>", r"\\b\\fs36 \1\\b0\\fs24\\par", rtf, flags=re.DOTALL)
            rtf = re.sub(r"<h2>(.*?)</h2>", r"\\b\\fs28 \1\\b0\\fs24\\par", rtf, flags=re.DOTALL)
            rtf = re.sub(r"<h3>(.*?)</h3>", r"\\b\\fs24 \1\\b0\\fs24\\par", rtf, flags=re.DOTALL)
            rtf = re.sub(r"<ul>\s*<li>(.*?)</li>\s*</ul>", r"\\bullet \1\\par", rtf, flags=re.DOTALL)
            rtf = re.sub(r"<br\s*/?>", r"\\par ", rtf)
            rtf = re.sub(r"<[^>]+>", "", rtf)
            rtf = (
                rtf.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", '"')
                .replace("&#39;", "'")
            )
            return rtf

        html = self._build_fragment()
        rtf_body = html_to_rtf(html)
        return "{\\rtf1\\ansi\\deff0\\fs24\n" + rtf_body + "\n}"


