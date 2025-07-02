from openai import OpenAI
import os


class OpenAIClientMixin:
    """Mixin for OpenAI client management and configuration."""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self._client = None

    def get_openai_client(self):
        """Get or create OpenAI client instance."""
        if self._client is None:
            if self.openai_api_key is not None:
                # Only set the environment variable if it was successfully retrieved
                os.environ["OPENAI_API_KEY"] = self.openai_api_key
            else:
                print("Warning: OPENAI_API_KEY environment variable is not set.")

            self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        return self._client

    def get_embeddings(self, query, client=None):
        """Generate embeddings for the given query."""
        if client is None:
            client = self.get_openai_client()

        embeddings = client.embeddings.create(
            model="text-embedding-ada-002",
            input=[query],
        )

        return embeddings.data[0].embedding
