# API Authentication Guide

This application now includes passcode-based authentication for all API endpoints.

## Environment Configuration

Set the `API_PASSCODE` environment variable to enable authentication:

```bash
# Windows (PowerShell)
$env:API_PASSCODE = "your-secure-passcode-here"

# Windows (Command Prompt)
set API_PASSCODE=your-secure-passcode-here

# Linux/Mac
export API_PASSCODE="your-secure-passcode-here"
```

## Client Usage

All API requests must include the passcode in the `X-Passcode` header:

```javascript
// Example JavaScript fetch request
fetch('/api/get_containers', {
    method: 'GET',
    headers: {
        'X-Passcode': 'your-secure-passcode-here',
        'Content-Type': 'application/json'
    }
})
.then(response => response.json())
.then(data => console.log(data));
```

```python
# Example Python requests
import requests

headers = {
    'X-Passcode': 'your-secure-passcode-here',
    'Content-Type': 'application/json'
}

response = requests.get('http://localhost:8080/get_containers', headers=headers)
```

```bash
# Example curl request
curl -H "X-Passcode: your-secure-passcode-here" \
     -H "Content-Type: application/json" \
     http://localhost:8080/get_containers
```

## Authentication Behavior

- **Missing passcode**: Returns `401 Unauthorized` with error message
- **Invalid passcode**: Returns `401 Unauthorized` with error message  
- **No `API_PASSCODE` set**: Authentication is disabled (development mode)

## Excluded Routes

The following routes do NOT require authentication:

- `/` (API documentation page)
- `/static/*` (Static files)
- Any route marked with `serve_static` endpoint

## Manual Authentication in Routes

If you need to manually handle authentication in a specific route, you can use the `authenticate_request()` function:

```python
def my_custom_route(self):
    # Manual authentication check
    auth_error = authenticate_request()
    if auth_error:
        return jsonify(auth_error[0]), auth_error[1]
    
    # Your route logic here
    return jsonify({"message": "Success"})
```

## Development vs Production

- **Development**: Set no `API_PASSCODE` environment variable to disable authentication
- **Production**: Always set a strong `API_PASSCODE` environment variable

## Security Recommendations

1. Use a strong, random passcode (at least 32 characters)
2. Use HTTPS in production to protect the passcode in transit
3. Rotate the passcode regularly
4. Never commit the passcode to version control
5. Use environment-specific configuration files or secret management systems

## Error Responses

Invalid or missing authentication returns:

```json
{
    "error": "Invalid or missing passcode"
}
```

With HTTP status code `401 Unauthorized`.
