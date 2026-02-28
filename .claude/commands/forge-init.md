# /forge-init — Configure Project

Interactively configure the Forge project. Ask the user for each setting,
then write the config files.

Gather from the user:
1. Project description (short)
2. Project requirements (detailed — or path to requirements file)
3. Mode: mvp / production-ready / no-compromise (default: mvp)
4. Strategy: auto-pilot / co-pilot / micro-manage (default: co-pilot)
5. Max cost cap in USD (default: 50)
6. Tech stack preferences: languages, frameworks, databases (optional)

Then:
- Write `config/team-config.yaml` with the values
- Write `config/project-requirements.md` with the requirements
- Run `bash $FORGE_DIR/scripts/init-project.sh --config config/team-config.yaml`
  to generate agent files
- Report: configuration saved, ready to `/forge-start`

$ARGUMENTS: none (interactive)
