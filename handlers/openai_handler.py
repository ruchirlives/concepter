from handlers.openai_mixins.client_mixin import OpenAIClientMixin
from handlers.openai_mixins.text_formatting_mixin import TextFormattingMixin
from handlers.openai_mixins.relationship_generation_mixin import RelationshipGenerationMixin
from handlers.openai_mixins.content_generation_mixin import ContentGenerationMixin
from handlers.openai_mixins.container_categorization_mixin import ContainerCategorizationMixin
from handlers.openai_mixins.relationship_extraction_mixin import RelationshipExtractionMixin


class OpenAIHandler(
    OpenAIClientMixin,
    TextFormattingMixin,
    RelationshipGenerationMixin,
    ContentGenerationMixin,
    ContainerCategorizationMixin,
    RelationshipExtractionMixin,
):
    """
    Modular OpenAI handler that combines all AI functionality through mixins.

    This class provides a unified interface for all OpenAI-related operations
    while keeping functionality separated into focused, testable mixins.
    """

    def __init__(self):
        super().__init__()


# Create a singleton instance for backward compatibility

# Export the singleton handler for all OpenAI operations
openai_handler = OpenAIHandler()
