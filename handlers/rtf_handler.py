from htmldocx import HtmlToDocx
from docx import Document
from io import BytesIO


class HTMLDocument:
    def get_rtf(self):
        """
        Convert the HTML content to RTF format for better compatibility with Microsoft OneNote.
        Requires the pypandoc library and a working Pandoc installation.
        """
        html_content = self.get_html()
        try:
            import pypandoc

            # pypandoc requires actual HTML, so we strip the clipboard markers if present
            # and just use the HTML fragment
            start = html_content.find("<!--StartFragment-->")
            end = html_content.find("<!--EndFragment-->")
            if start != -1 and end != -1:
                html_fragment = html_content[start + len("<!--StartFragment-->"): end]
            else:
                html_fragment = html_content
            rtf = pypandoc.convert_text(html_fragment, "rtf", format="html")
            return rtf
        except ImportError:
            raise ImportError(
                "pypandoc library is required for RTF conversion. Install it with 'pip install pypandoc' "
                "and ensure Pandoc is installed."
            )
        except OSError as e:
            raise RuntimeError(f"Pandoc is required for RTF conversion: {e}")

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

    def get_markdown(self):
        # Convert the HTML content to Markdown format.
        html_content = self.get_html()
        try:
            import html2text

            h = html2text.HTML2Text()
            h.ignore_links = False
            markdown = h.handle(html_content)
            return markdown
        except ImportError:
            raise ImportError("html2text library is required for Markdown conversion.")

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
