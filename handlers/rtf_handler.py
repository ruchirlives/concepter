from htmldocx import HtmlToDocx
from docx import Document
from io import BytesIO


class HTMLDocument:
    def get_simple_rtf(self):
        """
        Generate a simple RTF string from the document content for OneNote compatibility.
        Supports basic headings, paragraphs, and bullet points.
        """
        def html_to_rtf(html):
            # Very basic HTML to RTF conversion for supported tags
            import re
            rtf = html
            # Headings
            rtf = re.sub(r'<h1>(.*?)</h1>', r'\\b\\fs36 \1\\b0\\fs24\\par', rtf, flags=re.DOTALL)
            rtf = re.sub(r'<h2>(.*?)</h2>', r'\\b\\fs28 \1\\b0\\fs24\\par', rtf, flags=re.DOTALL)
            rtf = re.sub(r'<h3>(.*?)</h3>', r'\\b\\fs24 \1\\b0\\fs24\\par', rtf, flags=re.DOTALL)
            # Bullets
            rtf = re.sub(r'<ul>\s*<li>(.*?)</li>\s*</ul>', r'\\bullet \1\\par', rtf, flags=re.DOTALL)
            # Paragraphs and line breaks
            rtf = re.sub(r'<br\s*/?>', r'\\par ', rtf)
            # Remove any other tags
            rtf = re.sub(r'<[^>]+>', '', rtf)
            # Unescape HTML entities (basic)
            rtf = rtf.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
            return rtf

        # Join content and convert
        html = ''.join(self.content)
        rtf_body = html_to_rtf(html)
        # RTF header and footer
        rtf = '{\\rtf1\\ansi\\deff0\\fs24\n' + rtf_body + '\n}'
        return rtf

    def __init__(self):
        # Initialize the HTML content with the basic structure
        self.content = []

    def add_content(self, text, tag=None, newline=True):
        # Add content with optional HTML tag
        if tag:
            self.content.append(f"<{tag}>{text}</{tag}>")
        else:
            self.content.append(f"{text}")
        if newline:
            self.content.append("<br>")

    def add_bullet(self, text):
        # Adding a bullet point
        self.content.append(f"<ul><li>{text}</li></ul>")

    def get_html(self):
        # Closing the HTML content
        self.content.append("<!--EndFragment--></body></html>")
        html = "".join(self.content)
        start_html = html.find("<html>")
        start_fragment = html.find("<!--StartFragment-->")
        end_fragment = html.find("<!--EndFragment-->") + len("<!--EndFragment>")
        end_html = len(html)

        # Updating StartHTML, EndHTML, StartFragment, EndFragment positions
        html = html.replace("StartHTML:00000097", f"StartHTML:{start_html:08}")
        html = html.replace("EndHTML:00000000", f"EndHTML:{end_html:08}")
        html = html.replace("StartFragment:00000131", f"StartFragment:{start_fragment:08}")
        html = html.replace("EndFragment:00000000", f"EndFragment:{end_fragment:08}")

        return html

    def create_docx(self):
        # Convert the HTML content to a Word document.
        html_content = self.get_html()
        document = Document()
        converter = HtmlToDocx()
        converter.add_html_to_document(html_content, document)
        return document

    def get_doc(self):
        # Return the DOCX as an in-memory BytesIO stream.
        document = self.create_docx()
        file_stream = BytesIO()
        document.save(file_stream)
        file_stream.seek(0)
        return file_stream

    def save_doc(self, filename="output.docx"):
        # Save the DOCX to disk and return the filename.
        document = self.create_docx()
        document.save(filename)
        return filename


# Example usage
doc = HTMLDocument()
doc.add_content("My Document Title", "h1")
doc.add_content("This is an introduction paragraph.")
doc.add_content("Key Points", "h2")
doc.add_bullet("First important point")
doc.add_bullet("Second important point")
doc.add_content("Conclusion", "h2")
doc.add_content("This is the conclusion paragraph.")
