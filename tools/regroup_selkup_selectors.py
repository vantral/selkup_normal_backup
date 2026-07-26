"""Regroup Selkup annotation selectors without changing their tag inventory."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "conf" / "corpus.json"

LEGAL_GROUPS = [
    ("Agreement", ["1PL", "1PL.ADD", "1SG", "2PL", "2SG", "3", "3PL", "3SG"]),
    ("Particles", ["=ADD", "=CONTR", "=EMPH", "=ENCL", "=POL1", "=PTCL", "PART", "POL2"]),
    ("Cases", [
        "ABL", "ACC", "CAR", "COM", "DAT", "DAT.POSS.1SG", "DAT.POSS.2SG",
        "EL", "GEN", "ILL", "ILL2", "IN", "IN2", "LAT", "LAT2", "SIM",
    ]),
    ("Aspect", ["APROX", "ATT", "ITER1", "ITER2", "ITER3", "PUN", "SEM"]),
    ("Tense", [
        "AOR", "AOR.3PL", "AOR.3SG", "NPST.1PL", "NPST.1SG", "NPST.2PL",
        "NPST.2SG", "NPST.3PL", "NPST.3SG", "PRET", "RETR1", "RETR2",
    ]),
    ("Mood", ["DEB", "DEB.ADD", "DES", "IMP", "IMP.2PL", "JUSS.PL", "JUSS.SG", "OPT"]),
    ("Non-finite", [
        "CVB", "CVB.LIM", "CVB.POST", "CVB.SIM", "INF", "NACT", "NAG",
        "NMLZ", "NMLZ.ILL", "NMLZ.IN", "PTCP.ACT", "PTCP.PASS/NMLZ",
    ]),
    ("Valency derivation", ["CAUS", "CAUS.DIST", "DETR1", "DETR2", "MED"]),
    ("Denominal derivation", ["DEADJ", "DENOM", "DENOM1", "DENOM2", "INCH", "MAN"]),
    ("Nominal derivation", ["ADV", "ATTR", "ATTR.MEAS", "DEST", "FULL", "PROP", "STEM"]),
    ("Negation", ["NEG", "NEG.ATTR", "NEG.CVB", "NEG.PRET", "NEG.PTCP"]),
    ("Number", ["PL"]),
    ("Numerals", ["AGGR", "COLL", "ORD"]),
    ("Possessiveness", [
        "POSS.1PL", "POSS.1SG", "POSS.2PL", "POSS.2SG", "POSS.3PL", "POSS.3SG",
    ]),
    ("Other tags", ["CMPR", "INDEF1", "INDEF2", "INDEF3", "KIN", "RAR", "REFL", "SINCE"]),
]

SPOKEN_GROUPS = [
    ("Agreement", ["1", "2", "3", "OBJ", "SBJ", "PLOBJ", "PLSBJ"]),
    ("Number", ["SG", "PL", "COLL"]),
    ("Cases", ["ACC", "DAT", "ELA", "GEN", "ILL", "INS", "INSTR", "LOC", "PROL", "TRANSL"]),
    ("Aspect", ["ATTEN", "DUR", "HAB", "IPFV", "PFV", "PFV.INT", "PFV.REV"]),
    ("Tense/Mood", ["EVID", "FUT", "PST", "PSTN"]),
    ("Non-finite", ["CVB", "INF", "PRT.PST"]),
    ("Valency derivation", ["CAUS", "DETR", "TR"]),
    ("Nominal derivation", ["ADJ", "ADVZ", "DIM", "INCH", "NMLZ", "PEJ", "VBLZ"]),
    ("Particles", ["COORD", "FOC", "INT", "NEG", "NEG.EX", "RFL", "POSS"]),
    ("Other tags", ["EP", "MEL"]),
]


def regroup(selector, groups):
    items = {}
    for column in selector.get("columns", []):
        for item in column:
            if item.get("type") != "header" and item.get("value"):
                if item["value"] in items:
                    raise ValueError(f"Duplicate selector tag: {item['value']}")
                items[item["value"]] = item
    requested = [tag for unused_name, tags in groups for tag in tags]
    if len(requested) != len(set(requested)):
        raise ValueError("A tag occurs in more than one target group")
    missing = set(items) - set(requested)
    unknown = set(requested) - set(items)
    if missing or unknown:
        raise ValueError(f"Grouping mismatch; ungrouped={sorted(missing)}, absent={sorted(unknown)}")
    return {
        "columns": [
            [{"type": "header", "value": name, "tooltip": name}]
            + [items[tag] for tag in tags]
            for name, tags in groups
        ]
    }


def object_span(text, key):
    marker = f'"{key}"'
    key_pos = text.index(marker)
    start = text.index("{", key_pos + len(marker))
    depth = 0
    quoted = False
    escaped = False
    for pos in range(start, len(text)):
        char = text[pos]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, pos + 1
    raise ValueError(f"Unclosed JSON object for {key}")


def replace_object(text, key, value):
    start, end = object_span(text, key)
    line_start = text.rfind("\n", 0, start) + 1
    line_prefix = text[line_start:start]
    indent = line_prefix[: len(line_prefix) - len(line_prefix.lstrip())]
    lines = ["{", '  "columns": [']
    for column_index, column in enumerate(value["columns"]):
        lines.append("    [")
        for item_index, item in enumerate(column):
            comma = "," if item_index + 1 < len(column) else ""
            lines.append(
                "      " + json.dumps(item, ensure_ascii=False, separators=(", ", ": ")) + comma
            )
        column_comma = "," if column_index + 1 < len(value["columns"]) else ""
        lines.append("    ]" + column_comma)
    lines.extend(["  ]", "}"])
    rendered = "\n".join(lines)
    lines = rendered.splitlines()
    rendered = "\n".join([lines[0]] + [indent + line for line in lines[1:]])
    return text[:start] + rendered + text[end:]


def main():
    text = CONFIG.read_text(encoding="utf-8")
    data = json.loads(text)
    props = data["lang_props"]["selkup"]
    legal = any(
        item.get("value") == "=ADD"
        for column in props.get("gloss_selection", {}).get("columns", [])
        for item in column
    )
    groups = LEGAL_GROUPS if legal else SPOKEN_GROUPS
    selector_names = [
        name for name in ("gloss_selection", "gramm_selection")
        if props.get(name, {}).get("columns")
    ]
    for name in selector_names:
        replacement = regroup(props[name], groups)
        text = replace_object(text, name, replacement)
        props[name] = replacement
    json.loads(text)
    CONFIG.write_text(text, encoding="utf-8")
    print(f"Regrouped {', '.join(selector_names)} in {CONFIG}")


if __name__ == "__main__":
    main()
