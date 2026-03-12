# Setup

## Environment Setup Guide

Before using this repo, make sure you’ve completed this environment setup guide, which installs the core tools you’ll need for this module, such as:

- Git
- Git Bash (for Windows)
- Visual Studio Code
- UV

## Necessary Packages

The Deploying AI module uses its own isolated environment called `multi-agent-conversational-system-env` so that packages don’t conflict with other projects. We use **uv** to create this environment, activate it, and install the required packages listed in the module’s `pyproject.toml`.
This setup only needs to be done **once per module**, after that, you just activate the environment whenever you want to work in this repo.

Open a terminal (macOS/Linux) or Git Bash (Windows) in this repo, and run the following commands in order:

1. Create a virtual environment called `multi-agent-conversational-system-env`:

   ```
   uv venv multi-agent-conversational-system-env --python 3.12
   ```
2. Activate the environment:

   - for macOS/Linux:

     ```
     source multi-agent-conversational-system-env/bin/activate
     ```
   - for windows (git bash):

     ```
     source multi-agent-conversational-system-env/Scripts/activate
     ```
3. Install all required packages from the [pyproject.toml](./pyproject.toml)

   ```bash
   uv sync --active --link-mode=copy
   ```

> **Note:**
>
> - The `agentic-ai-chatbot-env` folder is intentionally created inside this repository.
> - This helps Visual Studio Code detect and attach the correct Python kernel automatically.
> - It’s not hidden because participants should be able to see it, understand its purpose, and, if needed, delete and recreate it.
> - The folder is safely listed in `.gitignore`, so it won’t be pushed to GitHub.

## Environment Usage

In order to run any code in this repo, you must first activate its environment.

- for macOS/Linux:

  ```
  source multi-agent-conversational-system-env/bin/activate
  ```
- for windows (git bash):

  ```
  source multi-agent-conversational-system-env/Scripts/activate
  ```

When the environment is active, your terminal prompt will change to show:

```
(multi-agent-conversational-system-env) $
```

This is your **visual cue** that you’re working inside the right environment.

When you’re finished, you can deactivate it with:

```bash
deactivate
```

> **👉 Remember**
> Only one environment can be active at a time. If you switch to a different repo, first deactivate this one (or just close the terminal) and then activate the new repo’s environment.
