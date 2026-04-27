#!/bin/sh

SKILL_NAME="codex-3p-switch"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

command="${1:-install}"
linked_platforms=""
removed_platforms=""
reminders=""
had_error=0

say() {
  printf '%s %s\n' "$1" "$2"
}

append_csv() {
  var_name=$1
  value=$2
  eval "current_value=\${$var_name}"
  if [ -n "$current_value" ]; then
    eval "$var_name=\$current_value,\\ \$value"
  else
    eval "$var_name=\$value"
  fi
}

resolve_dir() {
  if [ ! -d "$1" ]; then
    return 1
  fi
  (
    cd "$1" 2>/dev/null || exit 1
    pwd -P
  )
}

SCRIPT_REAL="$(resolve_dir "$SCRIPT_DIR")"

link_matches_script_dir() {
  target=$1
  if [ ! -L "$target" ]; then
    return 1
  fi

  target_real="$(resolve_dir "$target")" || return 1
  [ "$target_real" = "$SCRIPT_REAL" ]
}

link_target_text() {
  readlink "$1" 2>/dev/null || printf '%s' 'unknown target'
}

install_link() {
  label=$1
  base_dir=$2
  target="$base_dir/$SKILL_NAME"

  if [ -L "$target" ]; then
    if link_matches_script_dir "$target"; then
      say "→" "$label: already linked"
      append_csv linked_platforms "$label"
    else
      say "⚠" "$label: target points elsewhere ($(link_target_text "$target")); skipping"
    fi
    return
  fi

  if [ -e "$target" ]; then
    if [ -d "$target" ]; then
      say "⚠" "$label: target is an existing directory; skipping"
    else
      say "⚠" "$label: target exists and is not a symlink; skipping"
    fi
    return
  fi

  if ! mkdir -p "$base_dir"; then
    say "✗" "$label: failed to create parent directory $base_dir"
    had_error=1
    return
  fi

  if ln -s "$SCRIPT_DIR" "$target"; then
    say "✓" "$label: linked $target"
    append_csv linked_platforms "$label"
  else
    say "✗" "$label: failed to create symlink at $target"
    had_error=1
  fi
}

uninstall_link() {
  label=$1
  base_dir=$2
  target="$base_dir/$SKILL_NAME"

  if [ -L "$target" ]; then
    if link_matches_script_dir "$target"; then
      if rm "$target"; then
        say "✓" "$label: removed $target"
        append_csv removed_platforms "$label"
      else
        say "✗" "$label: failed to remove $target"
        had_error=1
      fi
    else
      say "⚠" "$label: target points elsewhere ($(link_target_text "$target")); skipping"
    fi
    return
  fi

  if [ -e "$target" ]; then
    say "⚠" "$label: target exists but is not a managed symlink; skipping"
  else
    say "→" "$label: nothing to remove"
  fi
}

status_link() {
  label=$1
  base_dir=$2
  target="$base_dir/$SKILL_NAME"

  if [ -L "$target" ]; then
    if link_matches_script_dir "$target"; then
      say "✓" "$label: linked"
      append_csv linked_platforms "$label"
    else
      say "⚠" "$label: linked elsewhere ($(link_target_text "$target"))"
    fi
    return
  fi

  if [ -e "$target" ]; then
    if [ -d "$target" ]; then
      say "⚠" "$label: real directory present at $target"
    else
      say "⚠" "$label: non-symlink file present at $target"
    fi
  else
    say "→" "$label: not installed"
  fi
}

handle_claude() {
  label="claude-code"
  base_dir="$HOME/.claude/skills"

  if [ ! -d "$HOME/.claude" ] && [ ! -d "$base_dir" ]; then
    if [ "$command" = "status" ]; then
      say "→" "$label: not detected"
    fi
    return
  fi

  case "$command" in
    install) install_link "$label" "$base_dir" ;;
    uninstall) uninstall_link "$label" "$base_dir" ;;
    status) status_link "$label" "$base_dir" ;;
  esac
}

handle_codex_canonical() {
  label="codex-canonical"
  base_dir="$HOME/.agents/skills"

  case "$command" in
    install) install_link "$label" "$base_dir" ;;
    uninstall) uninstall_link "$label" "$base_dir" ;;
    status) status_link "$label" "$base_dir" ;;
  esac
}

handle_terminal_tooling() {
  label="terminal-tooling"
  case "$command" in
    install)
      if bash "$SCRIPT_DIR/scripts/install.sh"; then
        append_csv linked_platforms "$label"
      else
        say "✗" "$label: install failed"
        had_error=1
      fi
      ;;
    uninstall)
      if bash "$SCRIPT_DIR/scripts/uninstall.sh"; then
        append_csv removed_platforms "$label"
      else
        say "✗" "$label: uninstall failed"
        had_error=1
      fi
      ;;
    status)
      if [ -x "$HOME/.local/bin/codex-mode-status" ] && [ -x "$HOME/.local/bin/codex-3p-config" ]; then
        say "✓" "$label: commands installed"
        append_csv linked_platforms "$label"
      else
        say "→" "$label: commands not installed"
      fi
      ;;
  esac
}

print_summary() {
  if [ -z "$linked_platforms" ]; then
    linked_platforms="none"
  fi
  if [ -z "$removed_platforms" ]; then
    removed_platforms="none"
  fi
  if [ -z "$reminders" ]; then
    reminders="none"
  fi

  case "$command" in
    uninstall)
      printf 'Removed from: %s. Reminders: %s.\n' "$removed_platforms" "$reminders"
      ;;
    *)
      printf 'Installed for: %s. Reminders: %s.\n' "$linked_platforms" "$reminders"
      ;;
  esac
}

case "$command" in
  install|status|uninstall)
    ;;
  *)
    say "✗" "Unknown command: $command"
    printf 'Usage: %s [install|status|uninstall]\n' "$0"
    exit 1
    ;;
esac

handle_claude
handle_codex_canonical
handle_terminal_tooling
print_summary

exit "$had_error"
