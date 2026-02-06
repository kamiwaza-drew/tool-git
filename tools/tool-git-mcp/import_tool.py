#!/usr/bin/env python3
"""Import tool-git-mcp into Kamiwaza via API."""

import json
import requests
from pathlib import Path

# Disable SSL warnings for localhost
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load kamiwaza.json
kamiwaza_json = json.loads(Path("kamiwaza.json").read_text())

# Load docker-compose
compose_yml = Path("docker-compose.appgarden.yml").read_text()

# Create template payload
template = {
    "name": kamiwaza_json["name"],
    "version": kamiwaza_json["version"],
    "source_type": "local",  # Use "local" for manually imported tools
    "visibility": kamiwaza_json["visibility"],
    "description": kamiwaza_json["description"],
    "category": kamiwaza_json["category"],
    "tags": kamiwaza_json["tags"],
    "author": kamiwaza_json["author"],
    "license": kamiwaza_json["license"],
    "image": kamiwaza_json["image"],
    "risk_tier": kamiwaza_json["risk_tier"],
    "verified": kamiwaza_json["verified"],
    "capabilities": kamiwaza_json["capabilities"],
    "required_env_vars": kamiwaza_json["required_env_vars"],
    "env_defaults": kamiwaza_json["env_defaults"],
    "compose_yml": compose_yml,
}

# Import via API
base_url = "https://localhost"
endpoint = f"{base_url}/api/v1/apps/app_templates"

print("Importing tool-git-mcp into Kamiwaza...")
print(f"Template name: {template['name']}")
print(f"Template version: {template['version']}")

# Note: This requires authentication
# You may need to add auth headers depending on Kamiwaza configuration
response = requests.post(
    endpoint,
    json=template,
    verify=False,  # Skip SSL verification for localhost
    timeout=30
)

if response.status_code == 200:
    print("✅ Tool imported successfully!")
    result = response.json()
    print(f"Template ID: {result.get('id')}")
elif response.status_code == 401:
    print("❌ Authentication required. Please log in to Kamiwaza first.")
    print("   You can manually import the template via the UI or use authenticated requests.")
elif response.status_code == 409:
    print("⚠️  Tool already exists. Updating...")
    # Try to find existing template and update it
    list_response = requests.get(endpoint, verify=False)
    if list_response.status_code == 200:
        templates = list_response.json()
        existing = next((t for t in templates if t["name"] == template["name"]), None)
        if existing:
            update_endpoint = f"{endpoint}/{existing['id']}"
            update_response = requests.put(update_endpoint, json=template, verify=False)
            if update_response.status_code == 200:
                print("✅ Tool updated successfully!")
            else:
                print(f"❌ Update failed: {update_response.status_code}")
                print(update_response.text)
else:
    print(f"❌ Import failed: {response.status_code}")
    print(response.text)
