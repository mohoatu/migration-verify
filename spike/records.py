"""ĐƯỜNG ỐNG — đọc tệp, dựng bản ghi, ghép hai bên theo khoá.

Không có quyết định nghiệp vụ nào ở đây. Mọi thứ trong tệp này là thứ ai cũng viết
được và viết giống nhau. Tách riêng ra để **đếm được** nó chiếm bao nhiêu phần công
việc so với phần phân loại — đó là câu hỏi của cả spike.
"""

import json
from datetime import datetime
from decimal import Decimal

# Các cách viết ngày thường gặp khi hệ cũ và hệ mới không thống nhất định dạng.
# Đọc được ngày thành `date` là việc của ĐƯỜNG ỐNG, không phải của phân loại:
# `2026-06-03` và `03/06/2026` là **cùng một ngày**, không phải hai giá trị lệch.
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%m/%d/%Y", "%d-%m-%Y")


def load_schema(path):
    with open(path, encoding="utf-8") as f:
        s = json.load(f)
    s["volatile_fields"] = set(s.get("volatile", {}).get("fields", []))
    return s


def _coerce(raw, field):
    v = raw.strip()
    t = field["type"]
    if v == "":
        return None
    if t == "decimal":
        try:
            return Decimal(v)
        except Exception:
            return v
    if t == "integer":
        try:
            return int(v)
        except Exception:
            return v
    if t == "date":
        for fmt in field.get("formats", DATE_FORMATS):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                continue
        return v
    return v


def _split_fixed(line, schema):
    return [line[f["start"]: f["start"] + f["len"]] for f in schema["fields"]]


def _split_delimited(line, schema):
    parts = line.split(schema.get("delimiter", "|"))
    n = len(schema["fields"])
    # Đệm cho đủ: trường rỗng ở cuối dòng hay bị cắt mất khi ghi tệp.
    return (parts + [""] * n)[:n]


def parse(path, schema):
    """Trả về (danh sách bản ghi theo thứ tự tệp, các dòng tiêu đề)."""
    split = _split_fixed if schema.get("format", "fixed") == "fixed" else _split_delimited
    records, headers = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            # Dòng tiêu đề: không phải bản ghi. Giữ lại để so sánh riêng.
            if line.startswith("RUNSTAMP"):
                headers.append(line)
                continue
            rec = {}
            for fld, raw in zip(schema["fields"], split(line, schema)):
                rec[fld["name"]] = _coerce(raw, fld)
            records.append(rec)
    return records, headers


def key_of(rec, schema):
    return tuple(str(rec[k]) for k in schema["key"])


def align(left, right, schema):
    """Ghép hai danh sách bản ghi theo khoá.

    Ghép theo khoá chứ không theo số dòng — nhờ vậy khác biệt về **thứ tự** không
    tự biến thành hàng nghìn khác biệt giả, vốn là lý do `diff` vô dụng ở đây.

    Trả về (các cặp khớp, chỉ có bên trái, chỉ có bên phải, thứ tự có đổi không).
    """
    li = {key_of(r, schema): r for r in left}
    ri = {key_of(r, schema): r for r in right}

    common = [k for k in li if k in ri]
    only_left = [k for k in li if k not in ri]
    only_right = [k for k in ri if k not in li]

    left_order = [key_of(r, schema) for r in left if key_of(r, schema) in ri]
    right_order = [key_of(r, schema) for r in right if key_of(r, schema) in li]
    reordered = left_order != right_order

    return [(k, li[k], ri[k]) for k in common], only_left, only_right, reordered
