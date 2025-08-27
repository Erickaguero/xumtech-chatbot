#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, pathlib, sys, requests

def main():
    ap = argparse.ArgumentParser(description="Importar FAQs a /api/faq desde un JSON (lista de objetos).")
    ap.add_argument("json_path", help="Ruta al archivo JSON (UTF-8)")
    ap.add_argument("--base", default="http://127.0.0.1:8000", help="URL base del backend")
    ap.add_argument("--token", required=True, help="ADMIN_TOKEN para Authorization Bearer")
    args = ap.parse_args()

    p = pathlib.Path(args.json_path)
    if not p.exists():
        print(f"ERROR: no existe {p}", file=sys.stderr); sys.exit(1)

    try:
        items = json.loads(p.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        items = json.loads(p.read_text(encoding="utf-8-sig"))

    if not isinstance(items, list):
        print("ERROR: el JSON debe ser una lista de objetos {question, answer, tags?}", file=sys.stderr); sys.exit(1)

    ok = fail = 0
    for i, it in enumerate(items, 1):
        q = (it.get("question") or "").strip()
        a = (it.get("answer") or "").strip()
        t = it.get("tags") if isinstance(it.get("tags"), list) else None
        if not q or not a:
            print(f"[{i}] Saltado: falta question/answer", file=sys.stderr); fail += 1; continue
        r = requests.post(
            f"{args.base}/api/faq",
            headers={"Authorization": f"Bearer {args.token}"},
            json={"question": q, "answer": a, "tags": t},
            timeout=10
        )
        if r.ok:
            print(f"[{i}] OK → id={r.json().get('id')} · {q[:60]}")
            ok += 1
        else:
            print(f"[{i}] ERR {r.status_code}: {r.text}", file=sys.stderr); fail += 1
    print(f"\nResumen: {ok} OK, {fail} errores")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())