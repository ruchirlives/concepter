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
    RelationshipExtractionMixin
):
    """
    Modular OpenAI handler that combines all AI functionality through mixins.
    
    This class provides a unified interface for all OpenAI-related operations
    while keeping functionality separated into focused, testable mixins.
    """
    
    def __init__(self):
        super().__init__()


# Create a singleton instance for backward compatibility
_openai_handler = OpenAIHandler()

# Export functions for backward compatibility with existing code
get_openai_client = _openai_handler.get_openai_client
get_embeddings = _openai_handler.get_embeddings
format_text = _openai_handler.format_text
generate_relationship_description = _openai_handler.generate_relationship_description
generate_reasoning_argument = _openai_handler.generate_reasoning_argument
generate_piece_name = _openai_handler.generate_piece_name
categorize_containers = _openai_handler.categorize_containers
get_relationships_from_openai = _openai_handler.get_relationships_from_openai
distill_subject_object_pairs = _openai_handler.distill_subject_object_pairs
