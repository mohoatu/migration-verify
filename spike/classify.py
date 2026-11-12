"""PHÂN LOẠI — phần duy nhất trong spike này có giá trị thật.

So sánh hai giá trị thì ai cũng làm được. Câu hỏi đáng tiền là:

    Khác biệt này là **chấp nhận được** hay là **tiền sai**?

Một công cụ không trả lời được câu đó thì chỉ là `diff` có thêm màu — và nó đẩy
toàn bộ việc nặng sang cho người đọc báo cáo. Đó đúng là lý do các chương trình
migration chạy song song hai năm: không ai dám nói "chỗ lệch này không sao".

Bốn loại dưới đây lấy từ lỗi migration có thật, không phải nghĩ ra.
"""

from decimal import Decimal

# Mức nghiêm trọng, theo thứ tự tăng dần.
VOLATILE = "VOLATILE"    # đổi mỗi lần chạy, không bao giờ là lỗi
FORMATTING = "FORMATTING"  # cùng một giá trị, viết khác đi
ROUNDING = "ROUNDING"    # trong phạm vi một đơn vị nhỏ nhất của trường
BUSINESS = "BUSINESS"    # sai nghiệp vụ thật — chặn go-live
MISSING = "MISSING"      # có ở bản cũ, mất ở bản mới
EXTRA = "EXTRA"          # xuất hiện thêm ở bản mới

BLOCKING = {BUSINESS, MISSING, EXTRA}


def _one_ulp(scale):
    """Đơn vị nhỏ nhất biểu diễn được của một trường thập phân.

    `PIC S9(7)V99` chỉ giữ được tới 0,01. Lệch đúng bằng một đơn vị đó gần như
    luôn là hệ quả của việc COBOL **cắt** còn Java **làm tròn** — khác biệt về
    cách biểu diễn, không phải khác biệt về nghiệp vụ.
    """
    return Decimal(1).scaleb(-scale)


def classify_field(name, old, new, field, schema):
    """Trả về (loại, ghi chú) cho một trường lệch. `None` nghĩa là không lệch."""
    if old == new:
        return None

    if name in schema["volatile_fields"]:
        return VOLATILE, "declared run-variable"

    if field["type"] == "decimal" and isinstance(old, Decimal) and isinstance(new, Decimal):
        delta = abs(new - old)
        tol = _one_ulp(field.get("scale", 2))
        # Ghi chú để trung tính về ngôn ngữ — báo cáo in được cả tiếng Việt và
        # tiếng Anh, và dòng này xuất hiện trong cả hai.
        if delta <= tol:
            return ROUNDING, f"delta {delta} <= 1 unit ({tol})"
        return BUSINESS, f"delta {new - old} > 1 unit ({tol})"

    if field["type"] == "integer":
        return BUSINESS, f"integer off by {new - old}" if isinstance(old, int) else f"{old} -> {new}"

    # Chuỗi bằng nhau sau khi cắt khoảng trắng và bỏ phân biệt hoa/thường thì là
    # khác biệt về **cách viết**, không phải về nghiệp vụ. Vẫn phải báo — một mã
    # phân loại đổi hoa/thường có thể làm hệ phía sau khớp sai — nhưng không chặn.
    if isinstance(old, str) and isinstance(new, str):
        if old.strip().casefold() == new.strip().casefold():
            return FORMATTING, "same value, differs in whitespace or case"

    return BUSINESS, f"{old!r} -> {new!r}, no tolerance applies"


def classify_pair(key, old_rec, new_rec, schema):
    """Mọi khác biệt giữa hai bản ghi cùng khoá."""
    out = []
    for fld in schema["fields"]:
        name = fld["name"]
        verdict = classify_field(name, old_rec[name], new_rec[name], fld, schema)
        if verdict:
            kind, note = verdict
            out.append({
                "key": key, "field": name, "kind": kind,
                "old": old_rec[name], "new": new_rec[name], "note": note,
            })
    return out


# ─────────────────────────────────────────────────────────────── giới hạn đã biết
#
# Luật ROUNDING ở trên **sẽ che mất** một lỗi nghiệp vụ thật nếu lỗi đó tình cờ
# làm lệch đúng ≤ 0,01. Đây là đánh đổi có ý thức, không phải sơ suất: không có
# dung sai thì 1.013 bản ghi lệch do làm tròn sẽ chôn vùi 4 bản ghi sai thật, và
# báo cáo lại thành vô dụng y như `diff`.
#
# Cách bù, và là lý do spike này dùng được: lỗi nghiệp vụ hầu như luôn để lại dấu
# vết ở **một trường khác không phải tiền** — ở đây là `accrual_days`, một số
# nguyên lệch đúng 1. Vì vậy mọi lệch ở trường số nguyên đều bị xếp BUSINESS ngay,
# không có dung sai nào.
#
# Nói cách khác: **đừng tìm tiền sai, hãy tìm nguyên nhân sai.** Tiền là kết quả;
# số ngày, cờ trạng thái, số lần lặp mới là nguyên nhân — và chúng không có dung
# sai tự nhiên nào để nấp sau.
#
# Luật FORMATTING cũng là một đánh đổi: nếu hệ phía sau phân biệt hoa/thường khi
# khớp mã, thì `AP` → `ap` là lỗi thật mà ở đây bị xếp không-chặn. Vì vậy nó vẫn
# được **báo** chứ không bị bỏ qua như VOLATILE. Lược đồ nên cho khai những trường
# mã cần so sánh nghiêm ngặt từng ký tự — chưa làm, ghi lại để không quên.
