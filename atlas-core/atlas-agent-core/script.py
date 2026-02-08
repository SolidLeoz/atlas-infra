#!/usr/bin/env python3
"""
Sensitive Audit Scanner
- Eseguilo dalla root del repo: python3 scripts/sensitive_audit.py
- Restituisce una lista di (file, riga, categoria, match) per possibili dati sensibili hardcoded.

Caratteristiche:
- Ignora .env e .env.* (per evitare rumore e perché non vanno pushati comunque)
- Segnala IP hardcoded (incl. Tailscale 100.x.x.x)
- Segnala token/chiavi hardcoded (Influx, JWT, API key, Bearer, AWS, GitHub, Stripe, ecc.)
- Segnala blocchi di private key
- Segnala password hardcoded

Nota:
- Questo script NON sostituisce la revisione umana, ma ti crea una "todo list" rapida.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple


# ----------------------------
# Config di base
# ----------------------------

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".idea",
    ".vscode",
    "target",
    "vendor",
}

DEFAULT_EXCLUDE_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
    ".pdf",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".mp4", ".mov", ".avi", ".mkv",
    ".exe", ".dll", ".so", ".dylib",
    ".class", ".jar",
    ".bin",
}

# Se vuoi essere ancora più aggressivo, puoi includere:
# ".crt", ".pem", ".p12", ".pfx", ".jks" (ma spesso sono artefatti da non committare comunque).
DEFAULT_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB per evitare scan lenti e file giganteschi


# ----------------------------
# Modello risultato
# ----------------------------

@dataclass
class Finding:
    file: str
    line: int
    category: str
    match: str
    context: str


# ----------------------------
# Regex: IP, keys, tokens, password
# ----------------------------

def compile_patterns() -> List[Tuple[str, re.Pattern]]:
    """
    Restituisce una lista di pattern (categoria, regex compilata).
    L'idea è: matchare "indicatori forti" e "hardcoded assignment".
    """

    patterns: List[Tuple[str, str]] = []

    # --- Private keys (altissima criticità) ---
    patterns.append((
        "PRIVATE_KEY_BLOCK",
        r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----"
    ))

    # --- IP address (IPv4). Segnalazione generale ---
    # Nota: non validiamo ogni range, ma filtriamo 0-255 per ridurre falsi positivi.
    ipv4 = r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
    patterns.append(("IPV4_HARDCODED", ipv4))

    # --- Tailscale-like IP (CGNAT tipico; molti usano 100.x.x.x in lab) ---
    # Non tutti i 100.* sono Tailscale, ma è un ottimo indicatore di infra interna
    patterns.append(("TAILSCALE_LIKE_IP", r"\b100\.(?:\d{1,3})\.(?:\d{1,3})\.(?:\d{1,3})\b"))

    # --- Token / secret in assignment (chiave=valore / chiave: valore) ---
    # Cattura casi tipo:
    #   INFLUX_TOKEN=abc
    #   admin_password: "xxx"
    #   jwt_secret = '...'
    #   apiKey: ...
    #
    # NB: se il valore è "REPLACE_ME" o "CHANGEME" o vuoto, NON segnaliamo.
    patterns.append((
        "HARDCODED_SECRET_ASSIGNMENT",
        r"""(?ix)
        \b(
            token|secret|api[_-]?key|apikey|access[_-]?key|private[_-]?key|
            client[_-]?secret|bearer|password|passwd|pwd|
            influxdb[_-]?token|influx[_-]?token|
            gf[_-]?security[_-]?admin[_-]?password|
            docker[_-]?influxdb[_-]?init[_-]?(?:admin[_-]?token|password)
        )\b
        \s*
        (?:=|:)\s*
        (["']?)
        ([^\s"'\n\r#;]{6,}|[^"'\n\r]{6,})
        \1
        """
    ))

    # --- Authorization: Bearer <token> (hardcoded) ---
    patterns.append((
        "HARDCODED_BEARER_TOKEN",
        r"(?i)\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*\b"
    ))

    # --- JWT (eyJ...) ---
    patterns.append((
        "JWT_TOKEN",
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    ))

    # --- AWS keys (indicatori forti) ---
    patterns.append((
        "AWS_ACCESS_KEY_ID",
        r"\bAKIA[0-9A-Z]{16}\b"
    ))
    patterns.append((
        "AWS_SECRET_ACCESS_KEY_LIKE",
        r"(?i)\baws[_-]?secret[_-]?access[_-]?key\b\s*(?:=|:)\s*['\"]?[A-Za-z0-9\/+=]{30,}['\"]?"
    ))

    # --- GitHub token (ghp_, github_pat_) ---
    patterns.append((
        "GITHUB_TOKEN",
        r"\b(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ))

    # --- Stripe keys ---
    patterns.append((
        "STRIPE_SECRET_KEY",
        r"\bsk_(?:live|test)_[A-Za-z0-9]{20,}\b"
    ))

    # --- Generic hex/base64 secrets in obvious variable name context (più rumoroso) ---
    patterns.append((
        "SUSPICIOUS_LONG_SECRET",
        r"""(?ix)
        \b(secret|token|api[_-]?key|password)\b
        .*?
        ([A-Fa-f0-9]{32,}|[A-Za-z0-9\/\+=]{40,})
        """
    ))

    compiled: List[Tuple[str, re.Pattern]] = []
    for category, pat in patterns:
        compiled.append((category, re.compile(pat)))
    return compiled


# ----------------------------
# Helpers per scan
# ----------------------------

def is_env_file(path: Path) -> bool:
    """
    Ignora .env e .env.* ovunque nel progetto.
    """
    name = path.name
    return name == ".env" or name.startswith(".env.")


def should_skip_path(path: Path, root: Path, exclude_dirs: set, exclude_suffixes: set) -> bool:
    """
    Ritorna True se il path va ignorato (dir esclusa, suffisso binario, .env, ecc.).
    """
    # Ignora .env/.env.*
    if is_env_file(path):
        return True

    # Ignora directory escluse
    try:
        rel_parts = path.relative_to(root).parts
        if rel_parts and rel_parts[0] in exclude_dirs:
            return True
        # Se una qualunque parte del path è in exclude_dirs
        if any(part in exclude_dirs for part in rel_parts):
            return True
    except ValueError:
        # Se non è sotto root, per sicurezza skippa
        return True

    # Ignora suffissi binari comuni
    if path.suffix.lower() in exclude_suffixes:
        return True

    return False


def is_probably_binary(data: bytes) -> bool:
    """
    Heuristica semplice: se troviamo tanti null byte, o byte non testuali, probabilmente è binario.
    """
    if not data:
        return False
    # Se contiene NUL è quasi sicuramente binario
    if b"\x00" in data:
        return True
    # Se troppi byte fuori range "testuale" (tolleriamo tab/newline/carriage)
    text_like = sum(1 for b in data[:4096] if (32 <= b <= 126) or b in (9, 10, 13))
    ratio = text_like / max(1, len(data[:4096]))
    return ratio < 0.80


def sanitize_value(val: str, max_len: int = 140) -> str:
    """
    Riduce la stampa di un secret per evitare output troppo lungo.
    ATTENZIONE: questo output andrà in console — trattalo come sensibile.
    """
    v = val.strip()
    if len(v) <= max_len:
        return v
    return v[:max_len] + "…"


def is_placeholder_secret(val: str) -> bool:
    """
    Se è un placeholder tipo REPLACE_ME, CHANGEME, empty, ecc. non segnaliamo.
    """
    v = val.strip().strip("'\"").lower()
    if not v:
        return True
    placeholders = {
        "replace_me", "changeme", "change_me", "todo", "tbd",
        "your_token_here", "your-secret-here", "example", "dummy",
        "xxxxxxxx", "********", "<redacted>", "redacted"
    }
    return v in placeholders


def iter_files(root: Path, exclude_dirs: set, exclude_suffixes: set) -> Iterator[Path]:
    """
    Itera tutti i file sotto root.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        # Filtra directory escluse in-place per velocizzare os.walk
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs and not d.startswith(".git")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if should_skip_path(p, root, exclude_dirs, exclude_suffixes):
                continue
            yield p


def scan_file(path: Path, patterns: List[Tuple[str, re.Pattern]], max_size: int) -> List[Finding]:
    findings: List[Finding] = []

    try:
        st = path.stat()
        if st.st_size > max_size:
            return findings
    except OSError:
        return findings

    try:
        raw = path.read_bytes()
    except (OSError, PermissionError):
        return findings

    if is_probably_binary(raw):
        return findings

    # Decodifica robusta: utf-8 con fallback
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            return findings

    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        # Evita di scandire linee mega-lunghe (minimizza rumore)
        if len(line) > 5000:
            continue

        for category, rx in patterns:
            m = rx.search(line)
            if not m:
                continue

            # Per alcune regex prendiamo gruppo "valore"
            match_text = m.group(0)

            if category == "HARDCODED_SECRET_ASSIGNMENT":
                # gruppo 3/4: dipende dalla regex
                # regex: (name)(quote?)(value)
                try:
                    val = m.group(3)
                except IndexError:
                    val = match_text

                if is_placeholder_secret(val):
                    continue

                # Segnala come HARD-CODED
                findings.append(Finding(
                    file=str(path),
                    line=idx,
                    category=category + " (LIKELY_HARDCODED)",
                    match=sanitize_value(val),
                    context=sanitize_value(line)
                ))
                continue

            if category in {"SUSPICIOUS_LONG_SECRET", "AWS_SECRET_ACCESS_KEY_LIKE"}:
                # cerca un valore "lungo"
                # prendiamo ultimo gruppo se esiste
                val = None
                if m.lastindex:
                    val = m.group(m.lastindex)
                if val and is_placeholder_secret(val):
                    continue

                findings.append(Finding(
                    file=str(path),
                    line=idx,
                    category=category + " (POSSIBLY_HARDCODED)",
                    match=sanitize_value(val or match_text),
                    context=sanitize_value(line)
                ))
                continue

            # IP: segnala sempre (sono infra disclosure)
            if category in {"IPV4_HARDCODED", "TAILSCALE_LIKE_IP"}:
                findings.append(Finding(
                    file=str(path),
                    line=idx,
                    category=category,
                    match=match_text,
                    context=sanitize_value(line)
                ))
                continue

            # Tutto il resto
            findings.append(Finding(
                file=str(path),
                line=idx,
                category=category,
                match=sanitize_value(match_text),
                context=sanitize_value(line)
            ))

    return findings


def print_findings(findings: List[Finding], root: Path, show_context: bool) -> None:
    """
    Stampa findings in formato leggibile.
    """
    if not findings:
        print("[OK] Nessun match trovato con i pattern attuali.")
        return

    # Ordina per file/linea
    findings.sort(key=lambda f: (f.file, f.line, f.category))

    print(f"[!] Trovati {len(findings)} possibili dati sensibili.\n")

    for f in findings:
        rel = str(Path(f.file).relative_to(root)) if Path(f.file).is_relative_to(root) else f.file
        print(f"{rel}:{f.line} [{f.category}] -> {f.match}")
        if show_context:
            print(f"    {f.context}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan repository for possible sensitive/hardcoded secrets (ignores .env files)."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan (default: current directory)."
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=DEFAULT_MAX_FILE_SIZE_BYTES,
        help=f"Max file size in bytes to scan (default: {DEFAULT_MAX_FILE_SIZE_BYTES})."
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Show full matching line context (may print secrets to terminal)."
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Additional directory name to exclude (can be used multiple times)."
    )
    parser.add_argument(
        "--include-suffix",
        action="append",
        default=[],
        help="Only include files with this suffix (ex: --include-suffix .yml). If set, scans only these suffixes."
    )

    args = parser.parse_args()
    root = Path(args.root).resolve()

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | set(args.exclude_dir)
    exclude_suffixes = set(DEFAULT_EXCLUDE_SUFFIXES)

    patterns = compile_patterns()

    findings: List[Finding] = []

    include_suffixes = set(args.include_suffix or [])

    for path in iter_files(root, exclude_dirs, exclude_suffixes):
        if include_suffixes:
            if path.suffix not in include_suffixes:
                continue
        findings.extend(scan_file(path, patterns, args.max_size))

    print_findings(findings, root, args.show_context)

    # Exit code utile per CI: 0 se OK, 2 se findings
    return 2 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
