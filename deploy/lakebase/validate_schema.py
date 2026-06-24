#!/usr/bin/env python3
"""Structural validator for the Lakebase migrations — runnable without Postgres.

Real validation is `psql -f` against Lakebase, but this catches the cheap, high-value
mistakes now: unbalanced parens / dollar-quoted blocks, and — the one that matters most —
that EVERY tenant-scoped table (one with a tenant_id column) is actually covered by an
RLS policy in 0006. A table added without RLS is a cross-tenant leak; this fails loudly.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MIG = Path(__file__).resolve().parent / "migrations"
# tables that are intentionally cross-tenant (no tenant_id, no RLS)
GLOBAL_TABLES = {"behavior.global_corpus", "tenancy.tenants"}  # tenants has its own self policy


def _balanced(sql: str) -> list[str]:
    errs = []
    if sql.count("(") != sql.count(")"):
        errs.append(f"unbalanced parens: {sql.count('(')} ( vs {sql.count(')')} )")
    if sql.count("$$") % 2 != 0:
        errs.append(f"unbalanced $$ blocks: {sql.count('$$')}")
    return errs


def main() -> int:
    files = sorted(MIG.glob("*.sql"))
    if not files:
        print("no migrations found", file=sys.stderr)
        return 1
    errs: list[str] = []
    tenant_tables: set[str] = set()      # CREATE TABLE … with a tenant_id column
    all_tables: set[str] = set()

    for f in files:
        sql = f.read_text(encoding="utf-8")
        for e in _balanced(sql):
            errs.append(f"{f.name}: {e}")
        # parse CREATE TABLE blocks and check for a tenant_id column
        for m in re.finditer(r"CREATE TABLE IF NOT EXISTS\s+([\w.]+)\s*\((.*?)\n\);", sql, re.S):
            name, body = m.group(1), m.group(2)
            all_tables.add(name)
            if re.search(r"\btenant_id\b", body):
                tenant_tables.add(name)

    # the RLS file must list every tenant-scoped table (minus the ones with bespoke policies)
    rls = (MIG / "0006_rls_policies.sql").read_text(encoding="utf-8")
    covered = set(re.findall(r"'([\w]+\.[\w]+)'", rls))
    expected = {t for t in tenant_tables if t not in GLOBAL_TABLES}
    missing = expected - covered
    if missing:
        errs.append(f"RLS GAP: tenant tables not in 0006 policy loop: {sorted(missing)}")

    # sanity: global tables must NOT have a tenant_id (else they'd need RLS)
    for g in GLOBAL_TABLES & all_tables:
        # tenancy.tenants legitimately has tenant_id (its PK); only flag global_corpus
        if g == "behavior.global_corpus" and g in tenant_tables:
            errs.append("behavior.global_corpus has tenant_id but is declared cross-tenant")

    print(f"files: {len(files)} | tables: {len(all_tables)} | tenant-scoped: {len(tenant_tables)} | "
          f"RLS-covered: {len(covered)}")
    if errs:
        for e in errs:
            print("  FAIL:", e)
        return 1
    print("OK — parens/$$ balanced; every tenant table is RLS-covered in 0006.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
