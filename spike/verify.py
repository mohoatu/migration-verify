#!/usr/bin/env python3
"""ĐƯỜNG ỐNG — ghép mọi thứ lại và trả về mã thoát.

Mã thoát là thứ biến công cụ này thành **cổng chặn** trong CI, thay vì một báo cáo
nữa chẳng ai đọc.

Chạy:  python3 verify.py <tệp cũ> <tệp mới> <lược đồ.json> [--lang en|vi]
"""

import sys
from records import load_schema, parse, align, parse_trailer
from classify import classify_pair, classify_field, BUSINESS, MISSING, EXTRA, BLOCKING
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

    diffs.extend(compare_non_records(old_head, new_head, schema))

    print(render(diffs, len(pairs), reordered, old_head != new_head, lang=lang,
                 header_checked=bool(schema.get("trailer_fields"))))

    return 1 if any(d["kind"] in BLOCKING for d in diffs) else 0


def compare_non_records(old_lines, new_lines, schema):
    """Đối chiếu dòng tiêu đề và dòng tổng kiểm soát.

    Chúng không ghép theo khoá được, nhưng **vẫn phải khớp**. Đặc biệt là dòng
    trailer: số bản ghi và tổng tiền ở đó là hai con số kiểm toán nhìn trước
    tiên, nên lệch là phải chặn, không phải ghi chú một dòng rồi cho qua.
    """
    out = []
    key = ("(trailer)",)

    for i, (a, b) in enumerate(zip(old_lines, new_lines)):
        if a == b:
            continue
        ra, rb = parse_trailer(a, schema), parse_trailer(b, schema)
        if ra is None or rb is None:
            # Lược đồ chưa khai `trailer_fields`, nên không biết dòng này gồm
            # những trường nào. KHÔNG chặn ở đây: dòng tiêu đề thường chứa dấu
            # thời gian và đổi mỗi lần chạy, chặn vì nó thì công cụ hoá vô dụng.
            # Báo cáo nói rõ là có đổi và chưa kiểm được — xem `report.py`.
            continue
        for fld in schema["trailer_fields"]:
            nm = fld["name"]
            verdict = classify_field(nm, ra[nm], rb[nm], fld, schema)
            if verdict:
                kind, note = verdict
                out.append({"key": key, "field": nm, "kind": kind,
                            "old": ra[nm], "new": rb[nm], "note": note})

    # Số dòng không phải bản ghi khác nhau: một bên thiếu hẳn tiêu đề hoặc
    # trailer. Im lặng ở đây nghĩa là một tệp cụt vẫn báo ĐẠT.
    if len(old_lines) != len(new_lines):
        out.append({"key": key, "field": "(số dòng không phải bản ghi)",
                    "kind": BUSINESS, "old": len(old_lines), "new": len(new_lines),
                    "note": "thiếu hoặc thừa dòng tiêu đề / tổng kiểm soát"})
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv))
