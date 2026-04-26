---
name: codex-3p-switch
description: Use when local Codex needs shareable Desktop and CLI mode switching between the official OpenAI subscription and a custom third-party gateway, including interactive third-party setup.
---

# Codex 3P Switch

## Overview

This skill standardizes local Codex provider switching with eight shell commands. It separates Desktop mode from CLI mode, so the app and terminal can follow different providers when needed.

## Commands

- `codex-os-mode`
Set both Codex Desktop and Codex CLI to the official OpenAI subscription profile. The managed official profile can omit `model`, which means Codex uses the official recommended default model.

- `codex-3p-mode`
Set both Codex Desktop and Codex CLI to the configured third-party gateway profile.

- `codex-app-os-mode`
Set Codex Desktop only to the official profile.

- `codex-app-3p-mode`
Set Codex Desktop only to the third-party gateway profile.

- `codex-cli-os-mode`
Set Codex CLI only to the official profile.

- `codex-cli-3p-mode`
Set Codex CLI only to the third-party gateway profile.

- `codex-mode-status`
Show current Desktop mode, CLI mode, top-level profile, and third-party config summary.

- `codex-3p-config`
Interactive setup for the third-party gateway. It writes managed config, can store the gateway secret in a managed env file, updates the current shell startup file when possible, sets the GUI env for Codex Desktop, and can optionally switch both Desktop and CLI to third-party mode immediately. The official model prompt can be left empty to follow the official recommended default model.

## Workflow

1. Run `codex-3p-config` once on a machine that does not already have a working third-party gateway config.
2. Use the mode commands to switch Desktop, CLI, or both.
3. Restart Codex Desktop after changing Desktop mode if the app is already open.
4. Open a new shell after changing CLI mode if the current shell still has stale command resolution.

## Managed Files

- `~/.codex/config.toml`
- `~/.codex/provider-modes/state.json`
- `~/.codex/provider-modes/third-party.env`
- `~/.codex/tools/codex_mode.py`
- `~/.local/bin/codex`
- `~/.local/bin/codex-os-mode`
- `~/.local/bin/codex-3p-mode`
- `~/.local/bin/codex-app-os-mode`
- `~/.local/bin/codex-app-3p-mode`
- `~/.local/bin/codex-cli-os-mode`
- `~/.local/bin/codex-cli-3p-mode`
- `~/.local/bin/codex-mode-status`
- `~/.local/bin/codex-3p-config`

## Rules

- Prefer the mode commands over hand-editing `~/.codex/config.toml`.
- Treat the official profile and the third-party profile as the only supported shared modes.
- Keep third-party secrets in the managed env file or in the user environment, not in the skill docs.
- If CLI mode is set explicitly, the `codex` wrapper should inject the matching profile unless the user already passed `--profile`.
