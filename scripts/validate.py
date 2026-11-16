#!/usr/bin/env python3
"""Validate TOS package metadata for ttyd (official rules, guide ch.4/8/14).

iframe mode (embedded floating window, nginx port-proxy with WebSocket
upgrade headers): checks config.ini required fields, mutual exclusion of
type/open_path, id charset rules, category limits (official category IDs),
lang coverage (26 documented languages, advisory), icon SVG validity, and
path/port consistency with /etc/ttyd-web/ttyd-web.env seed. Exit code 0 = pass.
"""
import json
import os
import re
import sys

REQUIRED = ["id", "icon", "publisher", "exec", "version", "help",
            "category", "platform", "application_type", "user"]
LANG_BASELINE = [
    "zh-cn", "zh-hk", "en-us", "ko-kr", "ja-jp", "de-de", "fr-fr", "it-it",
    "es-es", "hu-hu", "pl-pl", "tr-tr", "ru-ru", "pt-pt", "cs-cz", "da-dk",
    "nl-nl", "nb-no", "sv-se", "el-gr", "ro-ro", "th-th", "vi-vn", "id-id",
    "ar-sa", "he-il",
]
OFFICIAL_CATEGORIES = {
    "Audio_Video_Entertainment", "Photography_Video", "Backup_Sync",
    "Development_Tools", "Utilities", "Web_Services", "Security",
    "Download", "Driver", "Artificial_Intelligence",
}
ID_FORBIDDEN_PREFIX = "tos"
ID_FORBIDDEN_WORDS = {"docker", "bin", "api", "admin"}
RESERVED_PORTS = {22, 80, 443, 445, 3306, 5050, 5432, 6379, 8181, 8443}

errors: list[str] = []
advisories: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    cfg = json.load(open("config.ini", encoding="utf-8"))

    for field in REQUIRED:
        if field not in cfg:
            err(f"missing required field: {field}")

    app_id = cfg.get("id", "")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,49}", app_id):
        err(f"id '{app_id}' violates charset rules (lowercase letters/digits/"
            "hyphen, must start with a letter, <=50 chars)")
    if app_id.startswith(ID_FORBIDDEN_PREFIX):
        err(f"id must not start with reserved prefix '{ID_FORBIDDEN_PREFIX}'")
    if app_id in ID_FORBIDDEN_WORDS:
        err(f"id must not be a generic keyword: {app_id}")

    if cfg.get("application_type") != "deb":
        err(f"application_type must be 'deb', got {cfg.get('application_type')!r}")
    if cfg.get("platform") not in ("x86_64", "aarch64"):
        err(f"platform must be x86_64 or aarch64, got {cfg.get('platform')!r}")
    if len(cfg.get("category", [])) > 3:
        err("category must have at most 3 entries")
    for c in cfg.get("category", []):
        if c not in OFFICIAL_CATEGORIES:
            advisories.append(f"category '{c}' is not an official category ID "
                              "(Appendix A) — may need pre-approval")
    if "type" in cfg and cfg.get("open_path"):
        err("type and open_path are mutually exclusive — choose only one")
    if not cfg.get("help"):
        err("help URL is mandatory and cannot be empty")

    # UI mode checks: iframe (embedded, nginx port-proxy with ws headers)
    path = cfg.get("path", "")
    env_port = None
    seed = open("packaging-extras/ttyd-web.env.default", encoding="utf-8").read()
    m = re.search(r"^TTYD_PORT=(\d+)", seed, re.M)
    if m:
        env_port = int(m.group(1))
    else:
        err("packaging-extras/ttyd-web.env.default missing TTYD_PORT")

    if cfg.get("open_path"):
        err("ttyd must use type=iframe (embedded terminal, no separate tab)")
    elif cfg.get("type") == "iframe":
        if path != f"/{app_id}/":
            err(f"iframe mode expects path '/{app_id}/', got {path!r}")
        conf_path = f"nginx/{app_id}.conf"
        if not os.path.exists(conf_path):
            err(f"iframe mode requires {conf_path} (platform nginx route)")
        else:
            conf_lines = [l for l in open(conf_path, encoding="utf-8").read().splitlines()
                          if not l.strip().startswith("#")]
            conf_code = "\n".join(conf_lines)
            if "location /" + app_id + "/" not in conf_code:
                err(f"{conf_path} missing location /{app_id}/ block")
            if "alias " in conf_code:
                err(f"{conf_path} must proxy (ttyd is a service, not static)")
            if env_port is not None and f"127.0.0.1:{env_port}/" not in conf_code:
                err(f"{conf_path} must proxy to 127.0.0.1:{env_port}/")
            # terminal needs a long-lived WebSocket — upgrade headers required
            if "$http_upgrade" not in conf_code or 'Connection "upgrade"' not in conf_code:
                err(f"{conf_path} missing WebSocket upgrade headers "
                    "(proxy_set_header Upgrade/Connection)")
        if env_port is None:
            err("TTYD_PORT missing from packaging-extras/ttyd-web.env.default")
        elif not (8000 <= env_port <= 19999):
            advisories.append(f"port {env_port} is outside the recommended 8000-19999 range")
    else:
        err("config.ini must declare type=iframe")

    # service unit: must consume the /etc seed and force --writable
    svc_path = "init.d/ttyd-web.service"
    if not os.path.exists(svc_path):
        err(f"missing {svc_path}")
    else:
        svc = open(svc_path, encoding="utf-8").read()
        if "EnvironmentFile=/etc/ttyd-web/ttyd-web.env" not in svc:
            err(f"{svc_path}: must load /etc/ttyd-web/ttyd-web.env (generated credential)")
        if "--writable" not in svc:
            err(f"{svc_path}: missing --writable (ttyd is read-only by default)")

    # lang coverage
    lang_path = f"{app_id}.lang"
    if not os.path.exists(lang_path):
        err(f"missing {lang_path}")
    else:
        content = open(lang_path, encoding="utf-8-sig").read()
        if "\r\n" in content:
            advisories.append("lang file should use LF endings")
        missing = [l for l in LANG_BASELINE if f"[{l}]" not in content]
        if missing:
            advisories.append(f"{len(missing)} documented languages missing: {', '.join(missing)}")
        for section in re.split(r"\n(?=\[)", content):
            sm = re.match(r"\[([a-z-]+)\]", section)
            if not sm:
                continue
            loc = sm.group(1)
            for key in ("name", "auth", "descript"):
                km = re.search(rf'^{key}\s*=\s*"([^"]*)"', section, re.M)
                if km is None or not km.group(1).strip():
                    err(f"{lang_path}: [{loc}] has empty or missing {key}")

    # icon
    icon_rel = cfg.get("icon", "").lstrip("/")
    if not os.path.exists(icon_rel):
        err(f"icon not found: {icon_rel}")
    else:
        svg = open(icon_rel, encoding="utf-8").read()
        if "<svg" not in svg or "</svg>" not in svg:
            err(f"{icon_rel} is not a valid SVG")
        if "viewBox" not in svg:
            err(f"{icon_rel} missing viewBox attribute")
        expected = f"{app_id}.svg"
        if os.path.basename(icon_rel) != expected:
            err(f"icon filename {os.path.basename(icon_rel)} should be {expected}")

    for e in errors:
        print(f"ERROR: {e}")
    for a in advisories:
        print(f"ADVISORY: {a}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(advisories)} advisory(ies)")
        return 1
    print("All validations passed" + (f" ({len(advisories)} advisories)" if advisories else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
