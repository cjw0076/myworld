#!/usr/bin/env python3
"""
aios_vault.py — Local credential vault for AIOS agents.

AES-256-GCM encryption, Argon2id key derivation.
Credentials stay on disk encrypted; agents get in-process values only.

Usage:
  python3 scripts/aios_vault.py init
  python3 scripts/aios_vault.py set <key>
  python3 scripts/aios_vault.py get <key>
  python3 scripts/aios_vault.py list
  python3 scripts/aios_vault.py delete <key>

DNA invariants:
  #1 recommendation-only: vault recommends credentials, never auto-injects
  #2 draft-first: set always requires explicit passphrase confirmation
  #7 privacy: vault data never leaves ~/.aios/vault/
"""

import argparse
import getpass
import json
import os
import secrets
import sys
from pathlib import Path

try:
    from argon2 import low_level as argon2_ll
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import keyring
except ImportError as e:
    print(f"ERROR: missing dependency — {e}")
    print("  pip install cryptography argon2-cffi keyring")
    sys.exit(1)

# ── vault layout ──────────────────────────────────────────────────────────────
DEFAULT_VAULT_DIR = Path.home() / ".aios" / "vault"
VAULT_ENC = "vault.enc"
VAULT_SALT = "vault.salt"
KEYRING_SERVICE = "aios-vault"
KEYRING_USER = "passphrase"
ARGON2_TIME = 3
ARGON2_MEM = 65536  # 64 MiB
ARGON2_PARA = 2
ARGON2_LEN = 32     # 256-bit key


def _vault_dir() -> Path:
    d = Path(os.environ.get("AIOS_VAULT_DIR", DEFAULT_VAULT_DIR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return argon2_ll.hash_secret_raw(
        passphrase.encode(),
        salt,
        time_cost=ARGON2_TIME,
        memory_cost=ARGON2_MEM,
        parallelism=ARGON2_PARA,
        hash_len=ARGON2_LEN,
        type=argon2_ll.Type.ID,
    )


def _load_salt(vault_dir: Path) -> bytes:
    salt_path = vault_dir / VAULT_SALT
    if not salt_path.exists():
        raise FileNotFoundError("Vault not initialized. Run: aios_vault.py init")
    return salt_path.read_bytes()


def _encrypt(key: bytes, data: bytes) -> bytes:
    nonce = secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(nonce, data, None)
    return nonce + ct


def _decrypt(key: bytes, blob: bytes) -> bytes:
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, ct, None)


def _get_passphrase(prompt: str = "Vault passphrase: ", *, cache: bool = True) -> str:
    if cache:
        cached = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        if cached:
            return cached
    pw = getpass.getpass(prompt)
    if cache and pw:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, pw)
    return pw


def _load_vault(vault_dir: Path, passphrase: str) -> dict:
    enc_path = vault_dir / VAULT_ENC
    if not enc_path.exists():
        raise FileNotFoundError("Vault not initialized. Run: aios_vault.py init")
    salt = _load_salt(vault_dir)
    key = _derive_key(passphrase, salt)
    try:
        blob = enc_path.read_bytes()
        plain = _decrypt(key, blob)
        return json.loads(plain.decode())
    except Exception:
        raise ValueError("Failed to decrypt vault — wrong passphrase or corrupted file")


def _save_vault(vault_dir: Path, passphrase: str, data: dict) -> None:
    salt = _load_salt(vault_dir)
    key = _derive_key(passphrase, salt)
    plain = json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
    blob = _encrypt(key, plain)
    enc_path = vault_dir / VAULT_ENC
    # write atomically
    tmp = enc_path.with_suffix(".tmp")
    tmp.write_bytes(blob)
    tmp.replace(enc_path)


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_init(args) -> None:
    vault_dir = _vault_dir()
    enc_path = vault_dir / VAULT_ENC
    salt_path = vault_dir / VAULT_SALT

    if enc_path.exists():
        print(f"Vault already exists at {vault_dir}")
        answer = input("Re-initialize? This will DESTROY all stored credentials [y/N]: ")
        if answer.strip().lower() != "y":
            print("Aborted.")
            return

    pw = getpass.getpass("New passphrase: ")
    pw2 = getpass.getpass("Confirm passphrase: ")
    if pw != pw2:
        print("ERROR: passphrases do not match")
        sys.exit(1)

    salt = secrets.token_bytes(32)
    salt_path.write_bytes(salt)
    salt_path.chmod(0o600)

    key = _derive_key(pw, salt)
    plain = json.dumps({}, ensure_ascii=False).encode()
    blob = _encrypt(key, plain)
    enc_path.write_bytes(blob)
    enc_path.chmod(0o600)

    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, pw)
    print(f"Vault initialized at {vault_dir}")
    print("  vault.enc  — encrypted credentials")
    print("  vault.salt — Argon2id salt (public, keep backed up)")
    print("Passphrase cached in OS keystore for this session.")


def cmd_set(args) -> None:
    key_name: str = args.key
    vault_dir = _vault_dir()
    passphrase = _get_passphrase()
    try:
        data = _load_vault(vault_dir, passphrase)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if key_name in data:
        overwrite = input(f"Key '{key_name}' already exists. Overwrite? [y/N]: ")
        if overwrite.strip().lower() != "y":
            print("Aborted.")
            return

    value = getpass.getpass(f"Value for '{key_name}': ")
    if not value:
        print("ERROR: empty value not allowed")
        sys.exit(1)

    data[key_name] = value
    _save_vault(vault_dir, passphrase, data)
    print(f"Stored: {key_name}")


def cmd_get(args) -> None:
    key_name: str = args.key
    vault_dir = _vault_dir()
    passphrase = _get_passphrase()
    try:
        data = _load_vault(vault_dir, passphrase)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if key_name not in data:
        print(f"ERROR: key '{key_name}' not found", file=sys.stderr)
        sys.exit(1)

    # print to stdout — caller receives the raw value
    print(data[key_name])


def cmd_list(args) -> None:
    vault_dir = _vault_dir()
    passphrase = _get_passphrase()
    try:
        data = _load_vault(vault_dir, passphrase)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if not data:
        print("Vault is empty.")
        return

    print(f"Stored credentials ({len(data)}):")
    for k in sorted(data.keys()):
        print(f"  {k}")


def cmd_delete(args) -> None:
    key_name: str = args.key
    vault_dir = _vault_dir()
    passphrase = _get_passphrase()
    try:
        data = _load_vault(vault_dir, passphrase)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if key_name not in data:
        print(f"ERROR: key '{key_name}' not found", file=sys.stderr)
        sys.exit(1)

    confirm = input(f"Delete '{key_name}'? [y/N]: ")
    if confirm.strip().lower() != "y":
        print("Aborted.")
        return

    del data[key_name]
    _save_vault(vault_dir, passphrase, data)
    print(f"Deleted: {key_name}")


def cmd_clear_cache(args) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
        print("Passphrase cache cleared.")
    except keyring.errors.PasswordDeleteError:
        print("No cached passphrase found.")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AIOS local credential vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  init          Create a new encrypted vault
  set KEY       Store a credential
  get KEY       Retrieve a credential (prints value to stdout)
  list          List all stored keys (values hidden)
  delete KEY    Remove a credential
  clear-cache   Clear the OS keystore passphrase cache
""",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Create a new encrypted vault")

    p_set = sub.add_parser("set", help="Store a credential")
    p_set.add_argument("key", help="Credential key name (e.g. OPENAI_API_KEY)")

    p_get = sub.add_parser("get", help="Retrieve a credential")
    p_get.add_argument("key", help="Credential key name")

    sub.add_parser("list", help="List all stored keys")

    p_del = sub.add_parser("delete", help="Remove a credential")
    p_del.add_argument("key", help="Credential key name")

    sub.add_parser("clear-cache", help="Clear the OS keystore passphrase cache")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    dispatch = {
        "init": cmd_init,
        "set": cmd_set,
        "get": cmd_get,
        "list": cmd_list,
        "delete": cmd_delete,
        "clear-cache": cmd_clear_cache,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
