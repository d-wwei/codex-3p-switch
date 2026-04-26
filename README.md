# codex-3p-switch

Shareable provider switching for Codex Desktop and Codex CLI.

It installs:

- a Codex skill: `$codex-3p-switch`
- a provider-mode controller script
- a `codex` wrapper so CLI mode can differ from Desktop mode
- eight shell commands:
  - `codex-os-mode`
  - `codex-3p-mode`
  - `codex-app-os-mode`
  - `codex-app-3p-mode`
  - `codex-cli-os-mode`
  - `codex-cli-3p-mode`
  - `codex-mode-status`
  - `codex-3p-config`

## Requirements

- macOS
- Codex CLI already installed
- Codex Desktop optional, but supported
- `zsh` or `bash`

## What It Does

- `codex-os-mode`
  Switch both Desktop and CLI to the official OpenAI subscription profile.

- `codex-3p-mode`
  Switch both Desktop and CLI to a third-party gateway profile.

- `codex-app-os-mode`
  Switch Desktop only to the official profile.

- `codex-app-3p-mode`
  Switch Desktop only to the third-party profile.

- `codex-cli-os-mode`
  Switch CLI only to the official profile.

- `codex-cli-3p-mode`
  Switch CLI only to the third-party profile.

- `codex-mode-status`
  Show current Desktop and CLI mode state.

- `codex-3p-config`
  Interactive setup for the third-party gateway. It can write managed config, write a managed env file, hook that env file into your shell startup file, set GUI env for Codex Desktop, and optionally switch both Desktop and CLI to third-party mode immediately.

## Quick Start

Install:

```bash
git clone https://github.com/d-wwei/codex-3p-switch.git
cd codex-3p-switch
./scripts/install.sh
```

Open a new shell, then check state:

```bash
codex-mode-status
```

Configure a third-party gateway:

```bash
codex-3p-config
```

Switch both Desktop and CLI to third-party:

```bash
codex-3p-mode
```

Switch both Desktop and CLI back to official:

```bash
codex-os-mode
```

## Install

```bash
git clone https://github.com/d-wwei/codex-3p-switch.git
cd codex-3p-switch
./scripts/install.sh
```

After install, open a new shell and run:

```bash
codex-mode-status
```

If you want to configure a third-party gateway:

```bash
codex-3p-config
```

## Command Reference

| Command | Effect |
|---|---|
| `codex-os-mode` | Desktop and CLI both use the official subscription |
| `codex-3p-mode` | Desktop and CLI both use the third-party gateway |
| `codex-app-os-mode` | Desktop only uses the official subscription |
| `codex-app-3p-mode` | Desktop only uses the third-party gateway |
| `codex-cli-os-mode` | CLI only uses the official subscription |
| `codex-cli-3p-mode` | CLI only uses the third-party gateway |
| `codex-mode-status` | Show current Desktop and CLI mode state |
| `codex-3p-config` | Interactive third-party gateway setup |

## Official Mode Model Behavior

Official mode does not pin a model by default. The managed official profile omits `model`, so Codex follows the official recommended default model.

## How It Works

- Desktop mode is controlled by the shared top-level profile in `~/.codex/config.toml`.
- CLI mode is controlled by a local `codex` wrapper that injects the matching profile when needed.
- Third-party gateway settings are stored in a managed block inside `~/.codex/config.toml`.
- Third-party secrets can be written to `~/.codex/provider-modes/third-party.env`.
- Desktop support for third-party credentials uses `launchctl setenv` so GUI apps can inherit the env var.

## FAQ

### Why do I need a new shell after install?

Because the installer adds `~/.local/bin` to your shell startup file. Existing shells do not automatically reload `PATH`.

### Why do I need to restart Codex Desktop after switching Desktop mode?

Because Codex Desktop reads its environment and shared config on launch. A running app will not always pick up the new provider state immediately.

### Does official mode force a specific model?

No. Official mode intentionally leaves `model` unset so Codex uses the official recommended default model.

### Does third-party mode force a specific model?

Yes. Third-party mode stores a model value in the managed third-party profile because gateways are often stricter and may not support the same defaults as OpenAI.

### Can Desktop and CLI use different providers at the same time?

Yes. That is the main purpose of the tool. For example:

```bash
codex-app-os-mode
codex-cli-3p-mode
```

### What files does this tool manage?

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

## Uninstall

```bash
./scripts/uninstall.sh
```

## License

MIT
