---
name: init
description: "Interactive project configuration wizard"
argument-hint: ""
---

# /forge:init — Project Setup

Launch the interactive project configuration wizard:

```bash
bash "$FORGE_DIR/scripts/init-project.sh" --wizard
```

This generates:

- `config/team-config.yaml` — Project configuration
- `config/project-requirements.md` — Project requirements document

Guide the user through project type, mode, strategy, tech stack, and team composition.

$ARGUMENTS
