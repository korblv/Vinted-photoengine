#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atjaunot.py — atjauno darba telpu no HANDOFF pakotnes.

Lietošana:
    python3 atjaunot.py 01_DZINEJS.md            # atjauno kodu uz /home/user/loop_bildes
    python3 atjaunot.py 01_DZINEJS.md --target /tmp/test
    python3 atjaunot.py 01_DZINEJS.md --check     # tikai pārbauda, neko neraksta

Pakotnes formāts (vienkāršs, bez atkarībām):
    === MANIFEST ===
    ceļš<TAB>baits<TAB>sha256
    === END MANIFEST ===
    === FILE: relative/path.py ===
    ...faila saturs burtiski...
    === END FILE ===

Nekas netiek pārrakstīts klusām: ja fails jau eksistē ar citu saturu,
skripts to pārsauc uz *.bak-<laiks>.
"""
import os
import sys
import hashlib
import time

MARK_MAN = "=== MANIFEST ==="
MARK_MAN_END = "=== END MANIFEST ==="
MARK_F = "=== FILE: "
MARK_F_END = "=== END FILE ==="


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def parse(path):
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    manifest = {}
    files = {}
    mode = None
    cur = None
    buf = []

    for ln in lines:
        if mode is None:
            if ln.rstrip(" \t") == MARK_MAN:
                mode = "manifest"
                continue
            if ln.startswith(MARK_F) and ln == ln.lstrip():
                mode = "file"
                cur = ln[len(MARK_F):].rstrip(" =").strip()
                buf = []
                continue
            continue

        if mode == "manifest":
            if ln.rstrip(" \t") == MARK_MAN_END:
                mode = None
                continue
            if not ln.strip():
                continue
            parts = ln.split("\t")
            if len(parts) == 3:
                manifest[parts[0].strip()] = (int(parts[1]), parts[2].strip())
            continue

        if mode == "file":
            if ln.rstrip(" \t") == MARK_F_END:
                files[cur] = "\n".join(buf)
                mode = None
                cur = None
                buf = []
                continue
            buf.append(ln)

    return manifest, files


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2

    bundle = args[0]
    target = "/home/user/loop_bildes"
    check_only = False
    i = 1
    while i < len(args):
        if args[i] == "--target" and i + 1 < len(args):
            target = args[i + 1]
            i += 2
        elif args[i] == "--check":
            check_only = True
            i += 1
        else:
            print("Nezināma opcija: %s" % args[i])
            return 2

    if not os.path.isfile(bundle):
        print("Nav atrasta pakotne: %s" % bundle)
        return 2

    manifest, files = parse(bundle)
    print("Pakotne : %s" % bundle)
    print("Faili   : %d" % len(files))
    print("Mērķis  : %s" % target)
    print("Režīms  : %s" % ("TIKAI PĀRBAUDE" if check_only else "RAKSTĪŠANA"))
    print("-" * 72)

    ok = 0
    bad = 0
    wrote = 0

    for name in sorted(files):
        data = (files[name] + "\n").encode("utf-8")
        got = sha256_bytes(data)
        exp = manifest.get(name)
        good = (exp is None) or (exp[1] == got)
        if good:
            ok += 1
        else:
            bad += 1

        mark = "OK " if good else "SHA!"
        extra = ""
        if not check_only:
            dst = os.path.join(target, name)
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            if os.path.isfile(dst):
                with open(dst, "rb") as fh:
                    if sha256_bytes(fh.read()) == got:
                        print("%s  %-42s (jau identisks)" % (mark, name))
                        continue
                os.replace(dst, dst + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
                extra = " (vecais -> .bak)"
            with open(dst, "wb") as fh:
                fh.write(data)
            wrote += 1
            extra += "  %d B" % len(data)
        print("%s  %-42s%s" % (mark, name, extra))

    print("-" * 72)
    print("Pārbaudīti: %d   OK: %d   SHA nesakrīt: %d   Ierakstīti: %d"
          % (len(files), ok, bad, wrote))

    missing = [m for m in manifest if m not in files]
    if missing:
        print("UZMANĪBU — manifestā ir, bet pakotnē nav: %s" % ", ".join(missing))
        bad += len(missing)

    if bad:
        print("REZULTĀTS: NEPILNĪGI — skat. rindas ar SHA!")
        return 1
    print("REZULTĀTS: VISS LABI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
