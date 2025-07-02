class ContentGenerationMixin:
    """Mixin for generating names, labels, and other content using AI."""
    
    def generate_piece_name(self, descriptions):
        """Generate a concise label for given descriptions."""
        client = self.get_openai_client()

        prompt = (
            "Generate a concise and really easy to comprehend label for the following text, "
            "re-using any acronyms, scheme names, or terminology that already appear in the text, "
            "but do not invent new acronyms or abbreviations. The label should capture the unique "
            "essence about the description, and avoid generic or broad wording, but use easy to "
            'understand phrases like "lack of data at local level", or "The need for [group x] to talk together". '
            "No quotes, just the label.:\n\n"
            f"{descriptions}\n\n"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "text"},
            temperature=1,
            max_completion_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            store=False,
        )
        
        return response.choices[0].message.content.strip()
