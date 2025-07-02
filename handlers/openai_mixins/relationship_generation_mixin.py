class RelationshipGenerationMixin:
    """Mixin for generating relationships and descriptions between entities."""
    
    def generate_relationship_description(self, subject=None, object=None):
        """Generate a description of the relationship between the subject and the object."""
        if subject is None or object is None:
            raise ValueError("Both subject and object must be provided.")
        
        client = self.get_openai_client()

        prompt = (
            "You are a helpful assistant whose ONLY job is to output a descriptive relationship text of max 30 words.\n"
            'Given the following subject and object, each with a "name" and a "description":\n'
            "Please describe the relationship between the two in a short sentence.\n"
            f"Subject: {subject}\n"
            f"Object: {object}\n"
            "Now strictly output the relationship description:"
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "text"},
            temperature=0.7,
            max_completion_tokens=1500,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            store=False,
        )
        
        return response.choices[0].message.content.strip()

    def generate_reasoning_argument(self, reasoning):
        """Generate a reasoning argument for the given reasoning."""
        client = self.get_openai_client()

        prompt = (
            "Please create a concise argument from the following graph reasoning chain. "
            "It needs to take the audience through a step by step yet concise understanding of the reasoning. "
            "Please prepend with an appropriate section title:\n"
            f"{reasoning}\n"
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "text"},
            temperature=0.7,
            max_completion_tokens=1500,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            store=False,
        )
        
        return response.choices[0].message.content.strip()
