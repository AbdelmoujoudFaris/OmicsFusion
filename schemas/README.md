# Schemas

`project.schema.json` is a JSON Schema for `project.yaml`, generated
directly from the pydantic model that actually validates it
(`omicsfusion.core.config.ProjectConfig`) — so it can never drift from the
real validation logic.

Regenerate after changing `src/omicsfusion/core/config.py`:

```bash
python -c "
import json
from omicsfusion.core.config import ProjectConfig
json.dump(ProjectConfig.model_json_schema(), open('schemas/project.schema.json', 'w'), indent=2)
"
```

## Editor integration

Point your editor's YAML schema support at this file for autocompletion
and inline validation while editing a `project.yaml`. For VS Code with the
YAML extension, add to your workspace settings:

```json
{
  "yaml.schemas": {
    "./schemas/project.schema.json": ["project.yaml", "**/config.yaml"]
  }
}
```
