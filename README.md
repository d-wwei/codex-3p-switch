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

## Official Mode Model Behavior

Official mode does not pin a model by default. The managed official profile omits `model`, so Codex follows the official recommended default model.

## Uninstall

```bash
./scripts/uninstall.sh
```
