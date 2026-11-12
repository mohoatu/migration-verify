"""ĐƯỜNG ỐNG — in báo cáo.

Yêu cầu duy nhất đáng nhớ: **người ký quyết định go-live không đọc log.** Báo cáo
phải trả lời được một câu, ở dòng đầu tiên: đi tiếp được hay không.

Hai ngôn ngữ, vì khách trên Upwork đọc tiếng Anh còn tài liệu nội bộ là tiếng Việt.
Chỉ chuỗi hiển thị khác nhau — logic phân loại dùng chung, không nhân bản.
"""

from collections import Counter
from classify import BLOCKING, BUSINESS, ROUNDING, VOLATILE, FORMATTING, MISSING, EXTRA

TEXT = {
    "vi": {
        VOLATILE: "Đổi theo lần chạy",
        FORMATTING: "Khác cách viết",
        ROUNDING: "Làm tròn / biểu diễn",
        BUSINESS: "SAI NGHIỆP VỤ",
        MISSING: "MẤT BẢN GHI",
        EXTRA: "THỪA BẢN GHI",
        "fail": "KHÔNG ĐẠT — {n} khác biệt phải xử lý, trên {r} bản ghi",
        "pass": "ĐẠT — mọi khác biệt đều giải thích được",
        "compared": "Đã so sánh   : {n} bản ghi",
        "order": "Thứ tự dòng  : ",
        "order_diff": "có đổi (đã ghép theo khoá, không tính là lệch)",
        "order_same": "giống nhau",
        "header": "Dòng tiêu đề : ",
        "changed": "có đổi",
        "same": "giống nhau",
        "by_kind": "Khác biệt theo loại",
        "blocks": "  ← chặn",
        "review": "Cần người xem — những chỗ này không giải thích được bằng kỹ thuật",
        "field": "  trường `{f}`: {n} bản ghi",
        "more": "  … và {n} chỗ nữa",
        "signoff": "Chấp nhận được, nhưng phải được ký duyệt",
        "signoff_1": "  {n} bản ghi lệch trong phạm vi một đơn vị nhỏ nhất của trường.",
        "signoff_2": "  Dấu hiệu điển hình của việc hệ cũ cắt số còn hệ mới làm tròn.",
        "signoff_3": "  Không phải lỗi logic — nhưng là thay đổi có thật với sổ sách.",
        "record": "(bản ghi)",
    },
    "en": {
        VOLATILE: "Run-variable",
        FORMATTING: "Formatting only",
        ROUNDING: "Rounding / representation",
        BUSINESS: "BUSINESS LOGIC CHANGED",
        MISSING: "RECORDS MISSING",
        EXTRA: "RECORDS ADDED",
        "fail": "DO NOT SHIP — {n} differences need a decision, across {r} records",
        "pass": "SHIP — every difference is explained",
        "compared": "Records compared : {n}",
        "order": "Record order     : ",
        "order_diff": "changed (matched by key, not counted as a difference)",
        "order_same": "identical",
        "header": "Header line      : ",
        "changed": "changed",
        "same": "identical",
        "by_kind": "Differences by class",
        "blocks": "  <- blocks",
        "review": "Needs a human — these cannot be explained away technically",
        "field": "  field `{f}`: {n} records",
        "more": "  ... and {n} more",
        "signoff": "Acceptable, but needs explicit sign-off",
        "signoff_1": "  {n} fields differ within one representable unit of the field.",
        "signoff_2": "  The classic signature of a system that truncated being replaced",
        "signoff_3": "  by one that rounds. Not a logic error — but a real ledger change.",
        "record": "(whole record)",
    },
}


def render(diffs, n_records, reordered, header_changed, sample=6, lang="vi"):
    t = TEXT[lang]
    counts = Counter(d["kind"] for d in diffs)
    blocking = [d for d in diffs if d["kind"] in BLOCKING]
    affected = len({d["key"] for d in blocking})

    L = []
    A = L.append

    A("=" * 70)
    A(t["fail"].format(n=len(blocking), r=affected) if blocking else t["pass"])
    A("=" * 70)
    A("")
    A(t["compared"].format(n=n_records))
    A(t["order"] + (t["order_diff"] if reordered else t["order_same"]))
    A(t["header"] + (t["changed"] if header_changed else t["same"]))
    A("")
    A(t["by_kind"])
    A("-" * 70)
    for kind in (BUSINESS, MISSING, EXTRA, ROUNDING, FORMATTING, VOLATILE):
        if counts.get(kind):
            mark = t["blocks"] if kind in BLOCKING else ""
            A(f"  {t[kind]:<26} {counts[kind]:>6}{mark}")
    A("")

    if blocking:
        A(t["review"])
        A("-" * 70)
        for field, n in Counter(d["field"] for d in blocking).most_common():
            A(t["field"].format(f=field, n=n))
        A("")
        for d in blocking[:sample]:
            k = "/".join(d["key"])           # khoá có thể gồm nhiều trường
            A(f"  {k}  {d['field']}: {d['old']} -> {d['new']}   ({d['note']})")
        if len(blocking) > sample:
            A(t["more"].format(n=len(blocking) - sample))
        A("")

    if counts.get(ROUNDING):
        A(t["signoff"])
        A("-" * 70)
        A(t["signoff_1"].format(n=counts[ROUNDING]))
        A(t["signoff_2"])
        A(t["signoff_3"])
        A("")

    return "\n".join(L)
