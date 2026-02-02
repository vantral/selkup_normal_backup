#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path


def split_morphemes(s: str):
    if not s:
        return []
    return [p for p in re.split(r"[-=]+", s) if p]


def build_gloss_index(parts: str, gloss: str):
    """
    Example:
      parts="bələ-d-də-n"
      gloss ="помогать-PROG-PST-3SG"
      -> "помогать{bələ}-PROG{d}-PST{də}-3SG{n}-"
    """
    ms = split_morphemes(parts)
    gs = split_morphemes(gloss)

    if not ms or not gs:
        return None  # nothing to do

    if len(ms) != len(gs):
        return "MISMATCH"

    out = []
    for g, m in zip(gs, ms):
        out.append(f"{g}{{{m}}}-")
    return "".join(out)


def main():
    json_files = sorted(Path(".").glob("*.json"))
    if not json_files:
        print("[ERROR] No .json files found in the current directory.")
        return

    total_changed = 0
    total_warn = 0

    for fp in json_files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] {fp.name}: cannot read JSON ({e})")
            total_warn += 1
            continue

        changed_in_file = 0

        sentences = data.get("sentences", [])
        for si, sent in enumerate(sentences):
            if sent.get("lang") != 0:
                continue
            for wi, w in enumerate(sent.get("words", [])):
                ana_list = w.get("ana")
                if not ana_list or not isinstance(ana_list, list):
                    continue

                ana0 = ana_list[0]
                parts = ana0.get("parts", "")
                gloss = ana0.get("gloss", "")

                idx = build_gloss_index(parts, gloss)
                if idx is None:
                    continue

                if idx == "MISMATCH":
                    # minimal warning, skip updating this token
                    print(f"[WARN] {fp.name}: sent#{si} word#{wi} morpheme mismatch: parts='{parts}' gloss='{gloss}'")
                    total_warn += 1
                    continue

                if ana0.get("gloss_index") != idx or ana0.get("gloss_index_ru") != idx:
                    ana0["gloss_index"] = idx
                    ana0["gloss_index_ru"] = idx
                    changed_in_file += 1

        if changed_in_file:
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] {fp.name}: updated {changed_in_file} ana item(s)")
            total_changed += changed_in_file
        else:
            print(f"[OK] {fp.name}: no changes")

    print(f"[DONE] total updated ana items: {total_changed}; warnings: {total_warn}")


if __name__ == "__main__":
    main()
