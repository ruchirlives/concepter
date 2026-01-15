# Instruction set ID handling notes

## Motivation
When the backend is responsible for generating new container identifiers, front-end clients still need a way to reference those soon-to-be-created nodes in subsequent instructions within the same payload (for example, adding children or relationships to a newly created container). Using ad-hoc temporary IDs like `temp-123` allows this, but forces the client to re-map every occurrence after the server returns real IDs.

## Suggested approach
A server-driven placeholder mapping keeps the API flexible without requiring the client to rewrite identifiers after the fact:

1. **Allow placeholders in creation instructions** (for example, `{ "action": "addNew", "id": "temp-123" }`). The placeholder is treated as a handle rather than a persisted ID.
2. **Generate real IDs during creation** and maintain a mapping of `placeholder -> real ID` on the server. The mapping is returned in the API response (`placeholderMapping`) so callers can update local caches.
3. **Rewrite subsequent instructions on the server** by replacing any occurrence of a placeholder with its resolved real ID before execution. This supports referencing new containers in later `addChild`, `modifyChild`, or relationship operations within the same request and keeps in-memory container instances free of placeholders.
4. **Apply the mapping to persisted structures** (e.g., `instances` entries or nested `containers` collections) as part of the same request cycle so no stale placeholders remain in storage.
5. **Return the mapping in the response** so clients can update their local state if they are caching identifiers.

## Benefits over client-side rewriting
- Clients only supply stable placeholders and do not need to orchestrate post-hoc rekeying.
- The backend can validate that all placeholders are resolved and fail fast if an instruction references an unknown placeholder.
- Mapping is consistent because it is produced alongside the actual creations that yielded the real IDs.

## Compatibility considerations
- Continue accepting explicit IDs for scenarios where clients pre-provision identifiers.
- Reserve a predictable namespace for placeholders (e.g., strings prefixed with `temp-`) to avoid collisions with real IDs.
- If multiple instruction batches are processed concurrently, keep the mapping scoped to a single request to avoid leaking placeholder substitutions across calls.
