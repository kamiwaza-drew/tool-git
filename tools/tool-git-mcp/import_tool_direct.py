#!/usr/bin/env python3
"""Import tool-git-mcp into Kamiwaza database directly."""

import json
import sys
from pathlib import Path

# Add kamiwaza to path
sys.path.insert(0, "/home/kamiwaza/kamiwaza")

from kamiwaza.serving.garden.apps.templates import TemplateService
from kamiwaza.serving.schemas.templates import CreateAppTemplate, TemplateSource, TemplateVisibility

# Load kamiwaza.json
tool_dir = Path(__file__).parent
kamiwaza_json = json.loads((tool_dir / "kamiwaza.json").read_text())

# Load docker-compose
compose_yml = (tool_dir / "docker-compose.appgarden.yml").read_text()

# Create template
template_data = CreateAppTemplate(
    name=kamiwaza_json["name"],
    version=kamiwaza_json["version"],
    source_type=TemplateSource.user_repo,  # Use "user_repo" for manually imported tools
    visibility=TemplateVisibility(kamiwaza_json["visibility"]),
    description=kamiwaza_json["description"],
    category=kamiwaza_json["category"],
    tags=kamiwaza_json["tags"],
    author=kamiwaza_json["author"],
    license=kamiwaza_json["license"],
    image=kamiwaza_json["image"],
    risk_tier=kamiwaza_json["risk_tier"],
    verified=kamiwaza_json["verified"],
    capabilities=kamiwaza_json["capabilities"],
    required_env_vars=kamiwaza_json["required_env_vars"],
    env_defaults=kamiwaza_json["env_defaults"],
    compose_yml=compose_yml,
)

# Create service and import template
print("Importing tool-git-mcp into Kamiwaza database...")
print(f"Template name: {template_data.name}")
print(f"Template version: {template_data.version}")

try:
    service = TemplateService()

    # Check if template already exists
    existing_templates = service.list_templates()
    existing = next((t for t in existing_templates if t.name == template_data.name), None)

    if existing:
        print(f"⚠️  Template already exists with ID: {existing.id}")
        print("   Updating existing template...")
        # Update the existing template
        from kamiwaza.serving.schemas.templates import UpdateAppTemplate
        update_data = UpdateAppTemplate(
            version=template_data.version,
            description=template_data.description,
            compose_yml=template_data.compose_yml,
            image=template_data.image,
            tags=template_data.tags,
            category=template_data.category,
            capabilities=template_data.capabilities,
            required_env_vars=template_data.required_env_vars,
            env_defaults=template_data.env_defaults,
        )
        result = service.update_template(existing.id, update_data)
        print(f"✅ Tool updated successfully!")
        print(f"   Template ID: {result.id}")
    else:
        result = service.create_template(template_data)
        print(f"✅ Tool imported successfully!")
        print(f"   Template ID: {result.id}")

    # Trigger tool servers initialization to update etcd
    from kamiwaza.util.garden import initialize_tool_servers
    initialize_tool_servers()
    print("✅ Tool servers re-initialized in etcd")

except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
