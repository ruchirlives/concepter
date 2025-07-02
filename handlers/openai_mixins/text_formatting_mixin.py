import markdown


class TextFormattingMixin:
    """Mixin for text formatting and processing operations."""
    
    def format_text(self, text: str) -> str:
        """Format markdown text to HTML."""
        # format markdown to html using the markdown library
        html = markdown.markdown(text, extensions=["markdown.extensions.tables"])

        # replace \n with <br> to maintain line breaks
        html = html.replace("\n", "<br>")

        return html
