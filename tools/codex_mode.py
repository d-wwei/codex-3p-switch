#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


MANAGED_BEGIN = "# BEGIN CODEX-PROVIDER-MODES MANAGED"
MANAGED_END = "# END CODEX-PROVIDER-MODES MANAGED"
SHELL_ENV_BEGIN = "# BEGIN CODEX-PROVIDER-MODES ENV"
SHELL_ENV_END = "# END CODEX-PROVIDER-MODES ENV"
DEFAULT_CONFIG = Path.home() / ".codex" / "config.toml"
STATE_DIR = Path.home() / ".codex" / "provider-modes"
STATE_FILE = STATE_DIR / "state.json"
ENV_FILE = STATE_DIR / "third-party.env"
BACKUP_DIR = STATE_DIR / "backups"
PROFILE_OS = "codex-provider-os"
PROFILE_3P = "codex-provider-3p"
PROVIDER_ID = "codexThirdPartyProvider"
PROVIDER_NAME = "Third-Party Provider"
DEFAULT_OFFICIAL_MODEL = ""
DEFAULT_3P_MODEL = "gpt-5.4"
DEFAULT_REASONING = "medium"
MODE_OS = "os"
MODE_3P = "3p"
KNOWN_TOP_LEVEL_COMMANDS = {
    "exec",
    "e",
    "review",
    "login",
    "logout",
    "mcp",
    "plugin",
    "mcp-server",
    "app-server",
    "app",
    "completion",
    "sandbox",
    "debug",
    "apply",
    "a",
    "resume",
    "fork",
    "cloud",
    "exec-server",
    "features",
    "help",
}


class ModeError(RuntimeError):
    pass


@dataclass
class ThirdPartySettings:
    base_url: str
    env_key: str
    third_party_model: str
    official_model: str
    reasoning_effort: str
    provider_id: str = PROVIDER_ID
    provider_name: str = PROVIDER_NAME
    wire_api: str = "responses"


def toml_string(value: str) -> str:
    return json.dumps(value)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_backup(path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"{path.name}.{stamp}.bak"
    if path.exists():
        shutil.copy2(path, backup)
    else:
        backup.write_text("", encoding="utf-8")
    return backup


def parse_simple_toml(text: str) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    root: dict[str, str] = {}
    sections: dict[str, dict[str, str]] = {}
    current = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
            sections.setdefault(current, {})
            continue
        match = re.match(r'([A-Za-z0-9_.-]+)\s*=\s*"((?:[^"\\]|\\.)*)"', stripped)
        if not match:
            continue
        key, raw_value = match.groups()
        value = bytes(raw_value, "utf-8").decode("unicode_escape")
        if current is None:
            root[key] = value
        else:
            sections.setdefault(current, {})[key] = value
    return root, sections


def split_managed_block(text: str) -> tuple[str, str]:
    begin = text.find(MANAGED_BEGIN)
    end = text.find(MANAGED_END)
    if begin == -1 or end == -1 or end < begin:
        return text.rstrip() + ("\n" if text else ""), ""
    end += len(MANAGED_END)
    before = text[:begin].rstrip() + "\n"
    managed = text[begin:end].rstrip() + "\n"
    return before, managed


def current_top_profile(text: str) -> str | None:
    before, _ = split_managed_block(text)
    root, _ = parse_simple_toml(before)
    return root.get("profile")


def remove_existing_profile_line(lines: list[str]) -> list[str]:
    out: list[str] = []
    removed = False
    for line in lines:
        stripped = line.strip()
        if not removed and re.match(r'profile\s*=\s*"[^"]+"', stripped):
            removed = True
            continue
        out.append(line)
    return out


def set_top_profile(text: str, profile: str) -> str:
    before, managed = split_managed_block(text)
    lines = remove_existing_profile_line(before.splitlines())

    insert_at = len(lines)
    for idx, line in enumerate(lines):
        if line.strip().startswith("["):
            insert_at = idx
            break

    prefix = lines[:insert_at]
    suffix = lines[insert_at:]

    if prefix and prefix[-1].strip():
        prefix.append("")
    prefix.append(f'profile = {toml_string(profile)}')
    if suffix and suffix[0].strip():
        prefix.append("")

    new_before = "\n".join(prefix + suffix).rstrip() + "\n"
    if managed:
        return new_before.rstrip() + "\n\n" + managed.rstrip() + "\n"
    return new_before


def managed_block(settings: ThirdPartySettings) -> str:
    os_model_line = f"model = {toml_string(settings.official_model)}\n" if settings.official_model else ""
    return (
        f"{MANAGED_BEGIN}\n"
        f"# Managed by codex-provider-modes.\n\n"
        f"[model_providers.{settings.provider_id}]\n"
        f"name = {toml_string(settings.provider_name)}\n"
        f"base_url = {toml_string(settings.base_url)}\n"
        f'env_key = {toml_string(settings.env_key)}\n'
        f"wire_api = {toml_string(settings.wire_api)}\n\n"
        f"[profiles.{PROFILE_OS}]\n"
        f"{os_model_line}"
        f'model_reasoning_effort = {toml_string(settings.reasoning_effort)}\n'
        f'model_provider = "openai"\n\n'
        f"[profiles.{PROFILE_3P}]\n"
        f"model = {toml_string(settings.third_party_model)}\n"
        f'model_reasoning_effort = {toml_string(settings.reasoning_effort)}\n'
        f"model_provider = {toml_string(settings.provider_id)}\n"
        f"{MANAGED_END}\n"
    )


def install_managed_block(text: str, settings: ThirdPartySettings) -> str:
    before, _ = split_managed_block(text)
    if before.strip():
        return before.rstrip() + "\n\n" + managed_block(settings)
    return managed_block(settings)


def load_managed_settings_from_block(text: str) -> ThirdPartySettings | None:
    _, managed = split_managed_block(text)
    if not managed:
        return None
    cleaned = "\n".join(
        line for line in managed.splitlines() if line.strip() not in {MANAGED_BEGIN, MANAGED_END}
    )
    _, sections = parse_simple_toml(cleaned)

    provider_section = sections.get(f"model_providers.{PROVIDER_ID}")
    os_profile = sections.get(f"profiles.{PROFILE_OS}")
    tp_profile = sections.get(f"profiles.{PROFILE_3P}")
    if not provider_section or not os_profile or not tp_profile:
        return None

    base_url = provider_section.get("base_url")
    env_key = provider_section.get("env_key")
    third_party_model = tp_profile.get("model")
    official_model = os_profile.get("model", "")
    reasoning_effort = tp_profile.get("model_reasoning_effort") or os_profile.get("model_reasoning_effort")
    if not base_url or not env_key or not third_party_model:
        return None

    return ThirdPartySettings(
        base_url=base_url,
        env_key=env_key,
        third_party_model=third_party_model,
        official_model=official_model,
        reasoning_effort=reasoning_effort or DEFAULT_REASONING,
        provider_name=provider_section.get("name") or PROVIDER_NAME,
        wire_api=provider_section.get("wire_api") or "responses",
    )


def detect_existing_settings(text: str) -> ThirdPartySettings | None:
    before, _ = split_managed_block(text)
    root, sections = parse_simple_toml(before)
    provider_name = root.get("model_provider")
    if not provider_name or provider_name == "openai":
        return None
    provider_section = sections.get(f"model_providers.{provider_name}")
    if not provider_section:
        return None
    base_url = provider_section.get("base_url")
    env_key = provider_section.get("env_key")
    if not base_url or not env_key:
        return None
    return ThirdPartySettings(
        base_url=base_url,
        env_key=env_key,
        third_party_model=root.get("model", DEFAULT_3P_MODEL),
        official_model=DEFAULT_OFFICIAL_MODEL,
        reasoning_effort=root.get("model_reasoning_effort", DEFAULT_REASONING),
        provider_name=provider_section.get("name") or PROVIDER_NAME,
        wire_api=provider_section.get("wire_api") or "responses",
    )


def ensure_settings_or_raise(path: Path, text: str) -> tuple[str, ThirdPartySettings, bool]:
    settings = load_managed_settings_from_block(text)
    if settings is not None:
        return text, settings, False
    detected = detect_existing_settings(text)
    if detected is None:
        raise ModeError("third-party provider is not configured yet; run `codex-3p-config` first")
    return install_managed_block(text, detected), detected, True


def launchctl_get(var: str) -> str:
    result = subprocess.run(
        ["launchctl", "getenv", var],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def launchctl_set(var: str, value: str) -> None:
    subprocess.run(["launchctl", "setenv", var, value], check=False)


def launchctl_unset(var: str) -> None:
    subprocess.run(["launchctl", "unsetenv", var], check=False)


def clear_gui_proxy(real: bool = True) -> list[str]:
    vars_to_clear = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]
    cleared: list[str] = []
    for var in vars_to_clear:
        if real:
            launchctl_unset(var)
        cleared.append(var)
    return cleared


def load_state() -> dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str)}


def save_state(desktop_mode: str | None = None, cli_mode: str | None = None) -> None:
    state = load_state()
    if desktop_mode:
        state["desktop_mode"] = desktop_mode
    if cli_mode:
        state["cli_mode"] = cli_mode
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def infer_desktop_mode(text: str) -> str:
    top_profile = current_top_profile(text)
    if top_profile == PROFILE_OS:
        return MODE_OS
    if top_profile == PROFILE_3P:
        return MODE_3P
    before, _ = split_managed_block(text)
    root, _ = parse_simple_toml(before)
    provider = root.get("model_provider")
    if provider == "openai":
        return "unmanaged(os-root)"
    if provider:
        return "unmanaged(3p-root)"
    return "unmanaged"


def apply_desktop_mode(path: Path, mode: str, clear_proxy: bool = True) -> int:
    text = read_text(path)
    prepared_text, settings, installed_now = ensure_settings_or_raise(path, text)
    target_profile = PROFILE_OS if mode == MODE_OS else PROFILE_3P
    new_text = set_top_profile(prepared_text, target_profile)
    backup = ensure_backup(path)
    write_text(path, new_text)
    save_state(desktop_mode=mode)

    cleared = clear_gui_proxy(real=True) if clear_proxy else []
    print(f"desktop_mode: {mode}")
    print(f"config: {path}")
    print(f"backup: {backup}")
    print(f"desktop_profile: {target_profile}")
    print(f"third_party_base_url: {settings.base_url}")
    if installed_now:
        print("installed managed profiles automatically")
    if cleared:
        print(f"cleared_gui_proxy: {', '.join(cleared)}")
    print("restart Codex Desktop if it is already open")
    return 0


def apply_cli_mode(path: Path, mode: str) -> int:
    text = read_text(path)
    prepared_text, _settings, installed_now = ensure_settings_or_raise(path, text)
    backup = None
    if installed_now:
        backup = ensure_backup(path)
        write_text(path, prepared_text)
    save_state(cli_mode=mode)
    print(f"cli_mode: {mode}")
    if installed_now:
        print(f"config: {path}")
        print(f"backup: {backup}")
        print("installed managed profiles automatically")
    print("new shells will use the updated CLI mode")
    return 0


def apply_both_modes(path: Path, mode: str, clear_proxy: bool = True) -> int:
    text = read_text(path)
    prepared_text, settings, installed_now = ensure_settings_or_raise(path, text)
    target_profile = PROFILE_OS if mode == MODE_OS else PROFILE_3P
    new_text = set_top_profile(prepared_text, target_profile)
    backup = ensure_backup(path)
    write_text(path, new_text)
    save_state(desktop_mode=mode, cli_mode=mode)

    cleared = clear_gui_proxy(real=True) if clear_proxy else []
    print(f"desktop_mode: {mode}")
    print(f"cli_mode: {mode}")
    print(f"config: {path}")
    print(f"backup: {backup}")
    print(f"desktop_profile: {target_profile}")
    print(f"cli_profile: {PROFILE_OS if mode == MODE_OS else PROFILE_3P}")
    print(f"third_party_base_url: {settings.base_url}")
    if installed_now:
        print("installed managed profiles automatically")
    if cleared:
        print(f"cleared_gui_proxy: {', '.join(cleared)}")
    print("restart Codex Desktop if it is already open")
    print("new shells will use the updated CLI mode")
    return 0


def find_real_codex() -> str:
    wrapper_override = os.environ.get("CODEX_WRAPPER_PATH")
    wrapper_path = Path(wrapper_override).resolve() if wrapper_override else (Path.home() / ".local" / "bin" / "codex").resolve()
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry).expanduser() / "codex"
        if not candidate.exists() or not os.access(candidate, os.X_OK):
            continue
        resolved = candidate.resolve()
        if resolved == wrapper_path:
            continue
        return str(resolved)
    raise ModeError("could not locate the real `codex` binary")


def has_explicit_profile(args: list[str]) -> bool:
    for arg in args:
        if arg in {"--profile", "-p"} or arg.startswith("--profile="):
            return True
    return False


def cli_profile_for_mode(mode: str) -> str | None:
    if mode == MODE_OS:
        return PROFILE_OS
    if mode == MODE_3P:
        return PROFILE_3P
    return None


def inject_profile_into_codex_args(args: list[str], profile: str) -> list[str]:
    if not args:
        return ["--profile", profile]

    first = args[0]
    if first in {"exec", "e", "review"}:
        return [first, "--profile", profile, *args[1:]]
    if first in KNOWN_TOP_LEVEL_COMMANDS and not first.startswith("-"):
        return args
    return ["--profile", profile, *args]


def do_dispatch_codex(args: argparse.Namespace) -> int:
    passthrough = list(args.args)
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    cmd = [find_real_codex()]
    cli_mode = load_state().get("cli_mode")
    profile = cli_profile_for_mode(cli_mode or "")
    if profile and not has_explicit_profile(passthrough):
        cmd.extend(inject_profile_into_codex_args(passthrough, profile))
    else:
        cmd.extend(passthrough)
    os.execv(cmd[0], cmd)
    return 0


def prompt_text(label: str, default: str | None = None, required: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if not value and default is not None:
            value = default
        if value or not required:
            return value
        print("value is required")


def prompt_official_model(current_value: str) -> str:
    if current_value:
        prompt = f"Official model [current: {current_value}; Enter for official recommended default]: "
    else:
        prompt = "Official model [Enter for official recommended default]: "
    return input(prompt).strip()


def prompt_secret(label: str) -> str:
    try:
        return getpass.getpass(f"{label}: ")
    except (EOFError, KeyboardInterrupt):
        print("", file=sys.stderr)
        raise


def prompt_yes_no(label: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        value = input(label + suffix).strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("please answer yes or no")


def detect_shell_rc() -> Path | None:
    shell = Path(os.environ.get("SHELL", "")).name
    if shell == "zsh":
        return Path.home() / ".zshrc"
    if shell == "bash":
        bashrc = Path.home() / ".bashrc"
        if bashrc.exists():
            return bashrc
        return Path.home() / ".bash_profile"
    return None


def ensure_shell_env_hook(rc_path: Path) -> Path:
    block = (
        f"{SHELL_ENV_BEGIN}\n"
        f'if [ -f "$HOME/.codex/provider-modes/third-party.env" ]; then\n'
        f'  . "$HOME/.codex/provider-modes/third-party.env"\n'
        "fi\n"
        f"{SHELL_ENV_END}\n"
    )
    text = read_text(rc_path)
    backup = ensure_backup(rc_path)
    begin = text.find(SHELL_ENV_BEGIN)
    end = text.find(SHELL_ENV_END)
    if begin != -1 and end != -1 and end > begin:
        end += len(SHELL_ENV_END)
        new_text = text[:begin].rstrip() + "\n" + block
    else:
        new_text = text.rstrip() + ("\n\n" if text.strip() else "") + block
    write_text(rc_path, new_text)
    return backup


def write_env_file(env_key: str, env_value: str) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# Managed by codex-provider-modes.\n"
        f"export {env_key}={shlex.quote(env_value)}\n"
    )
    write_text(ENV_FILE, content)
    ENV_FILE.chmod(0o600)


def print_command_guide() -> None:
    print("commands:")
    print("  codex-os-mode      -> Desktop and CLI use the official subscription")
    print("  codex-3p-mode      -> Desktop and CLI use the custom gateway")
    print("  codex-app-os-mode  -> Desktop only uses the official subscription")
    print("  codex-app-3p-mode  -> Desktop only uses the custom gateway")
    print("  codex-cli-os-mode  -> CLI only uses the official subscription")
    print("  codex-cli-3p-mode  -> CLI only uses the custom gateway")
    print("  codex-mode-status  -> Show current Desktop and CLI modes")


def do_3p_config(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    original_text = read_text(path)
    previous = load_managed_settings_from_block(original_text) or detect_existing_settings(original_text)

    defaults = previous or ThirdPartySettings(
        base_url="https://example.com/v1",
        env_key="CUSTOM_OPENAI_API_KEY",
        third_party_model=DEFAULT_3P_MODEL,
        official_model=DEFAULT_OFFICIAL_MODEL,
        reasoning_effort=DEFAULT_REASONING,
    )

    print("Configure a third-party gateway for Codex Desktop and CLI.")
    base_url = prompt_text("Third-party base URL", defaults.base_url, required=True)
    env_key = prompt_text("API key environment variable name", defaults.env_key, required=True)
    env_value = prompt_secret("API key value (optional; leave blank to keep current env setup)")
    third_party_model = prompt_text("Third-party model", defaults.third_party_model, required=True)
    official_model = prompt_official_model(defaults.official_model)
    reasoning_effort = prompt_text("Reasoning effort", defaults.reasoning_effort, required=True)

    settings = ThirdPartySettings(
        base_url=base_url,
        env_key=env_key,
        third_party_model=third_party_model,
        official_model=official_model,
        reasoning_effort=reasoning_effort,
    )

    backup = ensure_backup(path)
    new_text = install_managed_block(original_text, settings)
    write_text(path, new_text)
    print(f"wrote managed provider config to {path}")
    print(f"backup: {backup}")

    if env_value:
        if previous and previous.env_key != env_key:
            launchctl_unset(previous.env_key)
        write_env_file(env_key, env_value)
        launchctl_set(env_key, env_value)
        rc_path = detect_shell_rc()
        if rc_path is not None:
            rc_backup = ensure_shell_env_hook(rc_path)
            print(f"updated shell env hook: {rc_path}")
            print(f"shell backup: {rc_backup}")
        else:
            print(f"wrote env file: {ENV_FILE}")
            print("shell rc was not modified automatically; source the env file manually if needed")
    elif previous and previous.env_key != env_key:
        print("warning: env var name changed, but no new secret was provided")

    print_command_guide()
    if prompt_yes_no("Switch both Desktop and CLI to the custom gateway now?", default=False):
        return apply_both_modes(path, MODE_3P, clear_proxy=not args.no_clear_gui_proxy)
    print("no mode was switched")
    return 0


def do_status(args: argparse.Namespace) -> int:
    path = Path(args.config).expanduser()
    text = read_text(path)
    settings = load_managed_settings_from_block(text) or detect_existing_settings(text)
    state = load_state()
    desktop_mode = state.get("desktop_mode") or infer_desktop_mode(text)
    cli_mode = state.get("cli_mode") or "unmanaged"
    print(f"config: {path}")
    print(f"desktop_mode: {desktop_mode}")
    print(f"cli_mode: {cli_mode}")
    print(f"desktop_profile: {current_top_profile(text) or '(none)'}")
    print(f"managed_provider_config: {'yes' if load_managed_settings_from_block(text) else 'no'}")
    if settings:
        print(f"third_party_base_url: {settings.base_url}")
        print(f"third_party_env_key: {settings.env_key}")
        print(f"third_party_model: {settings.third_party_model}")
        print(f"official_model: {settings.official_model or '(official recommended default)'}")
        print(f"shell_env_present: {'yes' if os.environ.get(settings.env_key) else 'no'}")
        print(f"gui_env_present: {'yes' if launchctl_get(settings.env_key) else 'no'}")
    print(f"gui_http_proxy: {launchctl_get('HTTP_PROXY') or '(unset)'}")
    print(f"gui_https_proxy: {launchctl_get('HTTPS_PROXY') or '(unset)'}")
    return 0


def do_restart(_args: argparse.Namespace) -> int:
    subprocess.run(
        ["osascript", "-e", 'tell application "Codex" to quit'],
        check=False,
        capture_output=True,
        text=True,
    )
    subprocess.run(["open", "-a", "Codex"], check=False)
    print("requested Codex Desktop restart")
    return 0


def do_proxy_clear(_args: argparse.Namespace) -> int:
    cleared = clear_gui_proxy(real=True)
    print(f"cleared_gui_proxy: {', '.join(cleared)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Switch Codex Desktop and CLI provider modes")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Codex config.toml path (default: ~/.codex/config.toml)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("mode-status", help="Show current Desktop and CLI modes")
    sub.add_parser("restart-desktop", help="Restart Codex Desktop")
    sub.add_parser("proxy-clear", help="Clear GUI launchctl proxy variables")

    p3 = sub.add_parser("3p-config", help="Interactively configure a third-party gateway")
    p3.add_argument("--no-clear-gui-proxy", action="store_true")

    os_mode = sub.add_parser("os-mode", help="Switch Desktop and CLI to the official subscription")
    os_mode.add_argument("--no-clear-gui-proxy", action="store_true")

    tp_mode = sub.add_parser("3p-mode", help="Switch Desktop and CLI to the third-party gateway")
    tp_mode.add_argument("--no-clear-gui-proxy", action="store_true")

    app_os = sub.add_parser("app-os-mode", help="Switch Desktop only to the official subscription")
    app_os.add_argument("--no-clear-gui-proxy", action="store_true")

    app_tp = sub.add_parser("app-3p-mode", help="Switch Desktop only to the third-party gateway")
    app_tp.add_argument("--no-clear-gui-proxy", action="store_true")

    sub.add_parser("cli-os-mode", help="Switch CLI only to the official subscription")
    sub.add_parser("cli-3p-mode", help="Switch CLI only to the third-party gateway")

    dispatch = sub.add_parser("dispatch-codex", help="Internal wrapper for the real codex binary")
    dispatch.add_argument("args", nargs=argparse.REMAINDER)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "mode-status":
            return do_status(args)
        if args.command == "restart-desktop":
            return do_restart(args)
        if args.command == "proxy-clear":
            return do_proxy_clear(args)
        if args.command == "3p-config":
            return do_3p_config(args)
        if args.command == "os-mode":
            return apply_both_modes(Path(args.config).expanduser(), MODE_OS, clear_proxy=not args.no_clear_gui_proxy)
        if args.command == "3p-mode":
            return apply_both_modes(Path(args.config).expanduser(), MODE_3P, clear_proxy=not args.no_clear_gui_proxy)
        if args.command == "app-os-mode":
            return apply_desktop_mode(Path(args.config).expanduser(), MODE_OS, clear_proxy=not args.no_clear_gui_proxy)
        if args.command == "app-3p-mode":
            return apply_desktop_mode(Path(args.config).expanduser(), MODE_3P, clear_proxy=not args.no_clear_gui_proxy)
        if args.command == "cli-os-mode":
            return apply_cli_mode(Path(args.config).expanduser(), MODE_OS)
        if args.command == "cli-3p-mode":
            return apply_cli_mode(Path(args.config).expanduser(), MODE_3P)
        if args.command == "dispatch-codex":
            return do_dispatch_codex(args)
    except ModeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
