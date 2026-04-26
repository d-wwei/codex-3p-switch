#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SKILL_DIR="$CODEX_HOME/skills/codex-3p-switch"
TOOLS_DIR="$CODEX_HOME/tools"
BIN_DIR="$HOME/.local/bin"
TOOL_TARGET="$TOOLS_DIR/codex_mode.py"
PATH_MARKER_BEGIN="# BEGIN CODEX-3P-SWITCH PATH"
PATH_MARKER_END="# END CODEX-3P-SWITCH PATH"

write_wrapper() {
  local path="$1"
  local subcommand="$2"

  cat > "$path" <<EOF
#!/bin/zsh
exec "\$HOME/.codex/tools/codex_mode.py" $subcommand "\$@"
EOF
  chmod +x "$path"
}

write_codex_wrapper() {
  local path="$1"
  cat > "$path" <<'EOF'
#!/bin/zsh
CODEX_WRAPPER_PATH="$HOME/.local/bin/codex" exec "$HOME/.codex/tools/codex_mode.py" dispatch-codex -- "$@"
EOF
  chmod +x "$path"
}

update_shell_path() {
  local rc_file="$1"
  local block
  block=$(cat <<'EOF'
# BEGIN CODEX-3P-SWITCH PATH
export PATH="$HOME/.local/bin:$PATH"
# END CODEX-3P-SWITCH PATH
EOF
)

  mkdir -p "$(dirname "$rc_file")"
  touch "$rc_file"

  if grep -q "$PATH_MARKER_BEGIN" "$rc_file" 2>/dev/null; then
    python3 - <<'PY' "$rc_file" "$block" "$PATH_MARKER_BEGIN" "$PATH_MARKER_END"
from pathlib import Path
import sys
path = Path(sys.argv[1])
block = sys.argv[2]
begin = sys.argv[3]
end = sys.argv[4]
text = path.read_text(encoding="utf-8")
i = text.find(begin)
j = text.find(end)
if i != -1 and j != -1 and j > i:
    j += len(end)
    updated = text[:i].rstrip() + "\n" + block + "\n"
else:
    updated = text.rstrip() + ("\n\n" if text.strip() else "") + block + "\n"
path.write_text(updated, encoding="utf-8")
PY
  else
    printf '\n%s\n' "$block" >> "$rc_file"
  fi
}

mkdir -p "$SKILL_DIR/agents" "$TOOLS_DIR" "$BIN_DIR"

cp "$REPO_ROOT/SKILL.md" "$SKILL_DIR/SKILL.md"
cp "$REPO_ROOT/agents/openai.yaml" "$SKILL_DIR/agents/openai.yaml"
cp "$REPO_ROOT/tools/codex_mode.py" "$TOOL_TARGET"
chmod +x "$TOOL_TARGET"

write_codex_wrapper "$BIN_DIR/codex"
write_wrapper "$BIN_DIR/codex-os-mode" "os-mode"
write_wrapper "$BIN_DIR/codex-3p-mode" "3p-mode"
write_wrapper "$BIN_DIR/codex-app-os-mode" "app-os-mode"
write_wrapper "$BIN_DIR/codex-app-3p-mode" "app-3p-mode"
write_wrapper "$BIN_DIR/codex-cli-os-mode" "cli-os-mode"
write_wrapper "$BIN_DIR/codex-cli-3p-mode" "cli-3p-mode"
write_wrapper "$BIN_DIR/codex-mode-status" "mode-status"
write_wrapper "$BIN_DIR/codex-3p-config" "3p-config"

case "${SHELL:-}" in
  */zsh)
    update_shell_path "$HOME/.zshrc"
    ;;
  */bash)
    if [[ -f "$HOME/.bashrc" ]]; then
      update_shell_path "$HOME/.bashrc"
    else
      update_shell_path "$HOME/.bash_profile"
    fi
    ;;
esac

echo "installed codex-3p-switch"
echo "skill: $SKILL_DIR"
echo "tool: $TOOL_TARGET"
echo "bin: $BIN_DIR"
echo
echo "open a new shell, then run:"
echo "  codex-mode-status"
