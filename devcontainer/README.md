# Autonomous Coding Sandbox

> **Attribution**: This devcontainer configuration is based on [banteg/agents](https://github.com/banteg/agents/tree/master/devcontainer).

A devcontainer for running Claude Code, Codex, Amp, and OpenCode in yolo mode.

## Requirements

- Docker (or [OrbStack](https://orbstack.dev/))
- devcontainer CLI (`npm install -g @devcontainers/cli`)

## Quickstart

Install: `./devcontainer/install.sh self-install`

Run `devc <repo>` or `devc .` inside project folder.

You're now in tmux with Claude, Codex, Amp, and OpenCode ready to go, with permissions preconfigured.

To use with VSCode, run `devc install <repo>` and choose "Reopen in Container" in the editor.
The built-in terminal will login inside the container.

## Notes

- **Overwrites `.devcontainer/`** on every run
- Default shell is bash, zsh also available
- Auth and history persist across rebuilds via Docker volumes
