"""
OpenAI Handler - Modular AI functionality for container operations.

This module provides a unified interface for all OpenAI-related operations
using a mixin-based architecture for better organization and maintainability.
"""

from handlers.openai_mixins.openai_handler_modular import (
    get_openai_client,
    get_embeddings,
    format_text,
    generate_relationship_description,
    generate_reasoning_argument,
    generate_piece_name,
    categorize_containers,
    get_relationships_from_openai,
    distill_subject_object_pairs,
    OpenAIHandler
)

# Re-export everything for backward compatibility
__all__ = [
    'get_openai_client',
    'get_embeddings',
    'format_text',
    'generate_relationship_description',
    'generate_reasoning_argument',
    'generate_piece_name',
    'categorize_containers',
    'get_relationships_from_openai',
    'distill_subject_object_pairs',
    'OpenAIHandler'
]
