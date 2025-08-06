# Transition Metadata API

This document describes the transition metadata API endpoints that allow saving, loading, and deleting transition metadata to/from MongoDB using the repository pattern.

## Endpoints

### 1. Save Transition Metadata

**Endpoint:** `POST /save_transition_metadata`

**Description:** Saves transition metadata as a JSON object to MongoDB using the repository pattern.

**Request Headers:**

- `Content-Type: application/json`
- `X-Passcode: <your_passcode>` (if authentication is enabled)

**Request Body:**
```json
{
  "metadata": {
    "transitions": [
      {
        "id": "transition_1",
        "name": "Project Planning",
        "from_state": "initial",
        "to_state": "planning",
        "timestamp": "2025-08-06T10:00:00Z",
        "description": "Initial project setup and planning phase"
      }
    ],
    "metadata": {
      "project_name": "ConcepterWeb",
      "version": "1.0.0",
      "created_by": "user",
      "last_updated": "2025-08-06T12:00:00Z"
    }
  }
}
```

**Response:**
```json
{
  "message": "Transition metadata saved successfully"
}
```

**Error Responses:**
- `400 Bad Request`: No metadata provided or invalid JSON
- `500 Internal Server Error`: Database or server error

### 2. Load Transition Metadata

**Endpoint:** `GET /load_transition_metadata`

**Description:** Loads transition metadata from MongoDB.

**Request Headers:**
- `X-Passcode: <your_passcode>` (if authentication is enabled)

**Response:**
```json
{
  "metadata": {
    "transitions": [
      {
        "id": "transition_1",
        "name": "Project Planning",
        "from_state": "initial",
        "to_state": "planning",
        "timestamp": "2025-08-06T10:00:00Z",
        "description": "Initial project setup and planning phase"
      }
    ],
    "metadata": {
      "project_name": "ConcepterWeb",
      "version": "1.0.0",
      "created_by": "user",
      "last_updated": "2025-08-06T12:00:00Z"
    }
  },
  "message": "Transition metadata loaded successfully"
}
```

**No Data Response:**
```json
{
  "metadata": null,
  "message": "No transition metadata found"
}
```

**Error Responses:**
- `500 Internal Server Error`: Database or server error

### 3. Delete Transition Metadata

**Endpoint:** `DELETE /delete_transition_metadata`

**Description:** Deletes transition metadata from MongoDB.

**Request Headers:**
- `X-Passcode: <your_passcode>` (if authentication is enabled)

**Response:**
```json
{
  "message": "Transition metadata deleted successfully"
}
```

**No Data Response:**
```json
{
  "message": "No transition metadata found to delete"
}
```

**Error Responses:**
- `404 Not Found`: No transition metadata found to delete
- `500 Internal Server Error`: Database or server error

## Implementation Details

### Database Storage

- **Collection:** `collections` (same as other project data)
- **Document Name:** `transition_metadata`
- **Storage Format:** JSON string in the `data` field
- **Document Type:** `transition_metadata` (stored in `type` field)

### Repository Pattern

The implementation follows the established repository pattern used throughout the application:

- **Repository Setup:** The MongoDB repository is configured once in `app.py` and assigned to `ConceptContainer.repository`
- **Shared Instance:** All parts of the application use the same repository instance through the container class
- **Abstract Interface:** `ContainerRepository` in `repository_handler.py` defines the contract
- **MongoDB Implementation:** `MongoContainerRepository` in `mongodb_handler.py` implements the interface
- **Methods:**
  - `save_transition_metadata(metadata: Dict[str, Any]) -> None`
  - `load_transition_metadata() -> Optional[Dict[str, Any]]`
  - `delete_transition_metadata() -> bool`

### Key Architecture Points

- **Single Repository Instance:** The mixin uses `self.container_class.repository` instead of creating new instances
- **Consistent with Existing Code:** Follows the same pattern as `save_project_to_db()`, `load_project_from_db()`, etc.
- **Repository Configuration Check:** All endpoints verify that the repository is properly configured
- **Error Handling:** Returns 500 status if repository is not configured

### Architecture Benefits

- **Separation of Concerns:** Business logic is separated from data persistence
- **Testability:** Easy to mock the repository for unit testing
- **Flexibility:** Can easily switch storage backends by implementing the repository interface
- **Consistency:** Follows the same pattern as project container storage

### Frontend Integration

The API is designed to work with the provided frontend JavaScript functions:

```javascript
// Save transition metadata
const saveTransitionMetadata = async (metadata) => {
    try {
        console.log("Saving transition metadata to API...");
        const response = await apiClient.post(`${getApiUrl()}/save_transition_metadata`, {
            metadata: metadata,
        });
        console.log("Transition metadata saved successfully:", response.data);
    } catch (e) {
        console.error('Failed to save transition metadata', e);
    }
};

// Load transition metadata
const loadTransitionMetadata = async () => {
    try {
        const response = await apiClient.get(`${getApiUrl()}/load_transition_metadata`);
        console.log("Transition metadata loaded successfully:", response.data);
        return response.data;
    } catch (e) {
        console.error('Failed to load transition metadata', e);
        return null;
    }
};
```

### Authentication

If the `API_PASSCODE` environment variable is set, all API endpoints require the `X-Passcode` header with the correct passcode value.

### Error Handling

The API includes comprehensive error handling for:
- Missing or invalid request data
- JSON parsing errors
- Database connection issues
- MongoDB operation failures

All errors are logged server-side and appropriate error messages are returned to the client.
