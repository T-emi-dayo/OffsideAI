#!/usr/bin/env python3
"""
scaffold.py — post-clone setup for projects created from this template.

Run this once after cloning via GitHub template:

    gh repo create my-agent --template your-username/project-template --private --clone
    cd my-agent
    python scaffold.py my-agent
"""

import sys
import shutil
from pathlib import Path


PROJECT_DIR = Path(__file__).parent

TEXT_EXTENSIONS = {".py", ".toml", ".md", ".yml", ".yaml", ".txt", ".json", ".example"}


def rename_placeholders(project_name: str) -> None:
    for path in PROJECT_DIR.rglob("*"):
        if path.is_file() and path.suffix in TEXT_EXTENSIONS:
            try:
                content = path.read_text(encoding="utf-8")
                if "OffsideAI" in content:
                    path.write_text(
                        content.replace("OffsideAI", project_name),
                        encoding="utf-8",
                    )
            except Exception:
                pass


def create_env() -> None:
    example = PROJECT_DIR / ".env.example"
    env = PROJECT_DIR / ".env"
    if example.exists() and not env.exists():
        shutil.copy(example, env)
        print("Created .env from .env.example")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    project_name = sys.argv[1]

    print(f"Setting up '{project_name}' ...")
    rename_placeholders(project_name)
    create_env()

    print("\nDone. Next steps:")
    print("  uv sync")
    print("  # fill in .env values, then start building")


if __name__ == "__main__":
    main()
