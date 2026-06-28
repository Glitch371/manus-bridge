---
name: blender-manager
description: Manage connection and automation for Blender via ManusBridge. Use when the user wants to control Blender 3D through a direct HTTP tunnel.
---

# Blender Manager

This skill enables Manus to control a local instance of Blender 3D. It bypasses standard MCP authentication issues by using direct HTTP communication through a tunnel.

## 1. Setup & Connection

### Prerequisites
- **Blender**: Must have the `ManusBridge` addon installed and active.
- **Tunnel**: ngrok or similar must be running to expose the local port.

### Connection Logic
When starting a new session, check for the presence of a tunnel URL in the project instructions or user message.

- **Blender Port**: 9999

## 2. Communication Protocol

Always use the `shell` tool with a Python script to communicate with the local Blender service. This avoids session-based authentication errors.

### Request Template (Python)
```python
import requests
import json

def send_command(url, command, port=9999):
    headers = {"ngrok-skip-browser-warning": "true"}
    payload = {"command": command}
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
```

## 3. Blender Automation Workflows

### Creating Objects
Use `bpy.ops.mesh.primitive_*_add()` for basic shapes. Always specify `location` and `size`/`radius`.

### Material Management
To apply materials, first create the material, then assign it to the active object's material slots.

## 4. Troubleshooting
- **Connection Refused**: Ensure `ManusBridge` is started in Blender (N-panel > Manus > Start).
- **Timeout**: Check if ngrok is still running and the URL is correct.
- **Auth Error**: Ignore the "Auth Failed" status in the Manus UI; use the direct Python method instead.
