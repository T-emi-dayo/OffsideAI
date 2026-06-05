# project-template

Reusable scaffold for Python agentic / LangGraph projects.

## Starting a new project

```bash
gh repo create my-agent --template your-username/project-template --private --clone
cd my-agent
python scaffold.py my-agent
uv sync
# fill in .env values, then start building
```

`scaffold.py` replaces the `OffsideAI` placeholder across all files and creates `.env` from `.env.example`. Delete it once setup is done.

## Structure

```
src/
├── agents/       # LangGraph nodes — extend base_node.py
├── config/       # App settings (pydantic-settings)
├── prompts/      # Prompt templates
├── schemas/      # Pydantic models: state, requests, responses
├── services/     # External integrations — extend base_service.py
├── tools/        # Tool implementations
└── utils/        # Logging, helpers
tests/
├── unit/
├── integration/
└── e2e/
```
