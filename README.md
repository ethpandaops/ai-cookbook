# ethPandaOps AI Cookbook

A centralized repository for AI documentation, commands, and tools used by the ethPandaOps team.

## Overview

This repository serves as a shared resource for the ethPandaOps team to store and maintain:
- Claude Code commands and workflows
- Documentation and guides
- Shared scripts and utilities
- Team conventions and best practices

## Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/ethpandaops/ai-cookbook.git
   cd ai-cookbook
   ```

2. Run the setup script to install Claude Code commands:
   ```bash
   ./setup.sh
   ```

3. The setup script will do the following:
- Copy all the commands `./claude-code/commands/*` files to `~/.claude/commands/ethpandaops/`

4. To update commands, simply run:
   ```bash
   git pull
   ```

## Structure

```
├── claude-code/
│   └── commands/          # Claude Code commands for the team
├── docs/                  # Team documentation
├── scripts/               # Shared scripts
├── setup.sh               # Installation script
└── README.md              # This file
```

## Usage

After running `setup.sh`, the commands will be available in Claude Code. You can use them by referencing the command name in your Claude Code sessions.

To add new commands:
1. Create or modify files in the `claude-code/commands/` directory
2. Commit and push your changes
3. Team members can update by running `git pull`

## Contributing

1. Create a branch for your changes
2. Add your commands, documentation, or scripts
3. Create a pull request for review
4. After approval, merge to main

## Support

For questions or issues, please create an issue in this repository or reach out to the ethPandaOps team.