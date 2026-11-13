#!/usr/bin/env python3
"""ĐƯỜNG ỐNG — ghép mọi thứ lại và trả về mã thoát.

Mã thoát là thứ biến công cụ này thành **cổng chặn** trong CI, thay vì một báo cáo
nữa chẳng ai đọc.

Chạy:  python3 verify.py <tệp cũ> <tệp mới> <lược đồ.json> [--lang en|vi]
"""

import sys
from records import load_schema, parse, align
from classify import classify_pair, MISSING, EXTRA, BLOCKING
from report import render, TEXT

# Windows mặc định ghi console bằng cp1252, và báo cáo có cả tiếng Việt lẫn ký tự
# kẻ khung — gặp nhau là `UnicodeEncodeError` và công cụ chết giữa chừng. Khách
# của công cụ này gần như chắc chắn chạy Windows, nên đây không phải chuyện nhỏ:
# một công cụ vỡ khi in kết quả thì không có kết quả nào cả.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    lang = "en" if "--lang=en" in argv[1:] else "vi"
    if len(args) != 3:
        print(__doc__)
        return 2

    old_path, new_path, schema_path = args
    schema = load_schema(schema_path)
    label = TEXT[lang]["record"]

    old_recs, old_head = parse(old_path, schema)
    new_recs, new_head = parse(new_path, schema)

    pairs, only_old, only_new, reordered = align(old_recs, new_recs, schema)

    diffs = []
    for key, o, n in pairs:
        diffs.extend(classify_pair(key, o, n, schema))
    for k in only_old:
        diffs.append({"key": k, "field": label, "kind": MISSING,
                      "old": "present", "new": "absent", "note": "dropped by the new system"})
    for k in only_new:
        diffs.append({"key": k, "field": label, "kind": EXTRA,
                      "old": "absent", "new": "present", "note": "only in the new system"})

    print(render(diffs, len(pairs), reordered, old_head != new_head, lang=lang))

    return 1 if any(d["kind"] in BLOCKING for d in diffs) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
