#!/bin/bash
set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SKILL_DIR="$CODEX_HOME/skills/codex-3p-switch"
TOOL_TARGET="$CODEX_HOME/tools/codex_mode.py"
STATE_DIR="$CODEX_HOME/provider-modes"
BIN_DIR="$HOME/.local/bin"

rm -rf "$SKILL_DIR"
rm -f "$TOOL_TARGET"
rm -f "$BIN_DIR/codex"
rm -f "$BIN_DIR/codex-os-mode"
rm -f "$BIN_DIR/codex-3p-mode"
rm -f "$BIN_DIR/codex-app-os-mode"
rm -f "$BIN_DIR/codex-app-3p-mode"
rm -f "$BIN_DIR/codex-cli-os-mode"
rm -f "$BIN_DIR/codex-cli-3p-mode"
rm -f "$BIN_DIR/codex-mode-status"
rm -f "$BIN_DIR/codex-3p-config"

echo "removed codex-3p-switch skill files"
echo "state directory was left in place: $STATE_DIR"
