#!/usr/bin/env python3
"""Sinh hai tệp kết quả giả lập: bản CŨ (COBOL) và bản MỚI (Java sau migration).

Spike này không nhằm làm sản phẩm. Nó nhằm trả lời đúng một câu:

    Khi so sánh kết quả trước và sau migration, bao nhiêu phần công việc là
    ĐƯỜNG ỐNG (đọc tệp, ghép bản ghi, in báo cáo) và bao nhiêu phần là
    PHÂN LOẠI khác biệt?

Nếu phân loại chiếm phần lớn và mỗi khách hàng lại cần luật riêng, thì hướng này
là **tư vấn** chứ không phải **sản phẩm** — và biết điều đó ngay bây giờ đáng giá
hơn biết sau sáu tháng.

Bài toán giả lập: tính lãi dồn hằng ngày cho 2.000 tài khoản tiết kiệm. Đây là
dạng job phổ biến nhất trong các hệ thống cũ còn sống: đọc bản ghi, tính tiền,
ghi báo cáo.

Bốn khác biệt được gieo vào bản mới, lấy từ những lỗi migration có thật:

  1. LÀM TRÒN  — COBOL `PIC S9(7)V99` **cắt** phần lẻ; Java `BigDecimal` mặc định
                 **làm tròn**. Lệch ≤ 0,01 ở rất nhiều bản ghi. Vô hại, nhưng phải
                 được ký duyệt chứ không được lặng lẽ bỏ qua.
  2. THỨ TỰ    — bản mới ghi theo thứ tự sắp xếp, bản cũ ghi theo thứ tự xử lý.
                 Cùng một tập bản ghi, khác thứ tự dòng.
  3. THỜI GIAN — dòng tiêu đề có dấu thời gian chạy. Luôn khác, luôn vô nghĩa.
  4. SAI NGHIỆP VỤ — vòng `UNTIL` của COBOL dịch nhầm thành `while` của Java, gây
                 thừa đúng một ngày lãi cho các tài khoản đáo hạn rơi vào biên.
                 Đây là lỗi IBM nêu trong nghiên cứu của họ, và là loại lỗi phải
                 **chặn go-live**.

Ba lỗi đầu chạy đúng, biên dịch được, test đơn vị xanh. Chỉ lỗi thứ tư là tiền sai.
Một công cụ chỉ biết `diff` sẽ chôn lỗi thứ tư dưới hàng nghìn dòng nhiễu từ ba lỗi
kia — và đó chính là lý do người ta chạy song song hai năm.

Chạy:  python3 generate.py
"""

import random
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from datetime import date, timedelta

random.seed(20261110)  # cố định để chạy lại cho cùng kết quả

N_ACCOUNTS = 2000
BASE_DATE = date(2026, 10, 1)


def money(x, rounding):
    """Quy về 2 chữ số lẻ. `rounding` là chỗ hai hệ thống khác nhau."""
    return Decimal(x).quantize(Decimal("0.01"), rounding=rounding)


def build_accounts():
    out = []
    for i in range(N_ACCOUNTS):
        acc = f"ACC{i:07d}"
        principal = Decimal(random.randrange(10_000, 5_000_000)) / Decimal(100)
        rate_bp = random.choice([125, 250, 375, 410, 500, 615])  # điểm cơ bản
        term_days = random.choice([30, 31, 60, 90, 91, 180, 365])
        start = BASE_DATE - timedelta(days=random.randrange(0, 400))
        out.append({
            "account_id": acc,
            "principal": principal,
            "rate_bp": rate_bp,
            "term_days": term_days,
            "start": start,
        })
    return out


def accrual_days(a, off_by_one):
    """Số ngày tính lãi.

    Hệ cũ dùng `PERFORM UNTIL day > term` — dừng *sau* khi vượt, nên đếm đúng term.
    Bản dịch dùng `while (day <= term)` nhưng khởi tạo lệch một, nên với các tài
    khoản đáo hạn đúng vào biên thì thừa một ngày.
    """
    elapsed = (BASE_DATE - a["start"]).days
    days = min(elapsed, a["term_days"])
    # Lỗi thật chỉ chạm các tài khoản đáo hạn **đúng vào biên** — hiếm, nằm lẫn
    # giữa hàng trăm bản ghi chỉ lệch do làm tròn. Đó mới là hình dạng thật của
    # một lỗi migration: không phải sai hàng loạt, mà sai một nhóm nhỏ, lặng lẽ.
    if off_by_one and elapsed == a["term_days"]:
        days += 1
    return max(days, 0)


def compute(a, modern):
    days = accrual_days(a, off_by_one=modern)
    raw = a["principal"] * Decimal(a["rate_bp"]) / Decimal(10_000) * Decimal(days) / Decimal(365)
    # Khác biệt #1: hệ cũ cắt, hệ mới làm tròn.
    interest = money(raw, ROUND_HALF_UP if modern else ROUND_DOWN)
    total = money(a["principal"] + interest, ROUND_HALF_UP if modern else ROUND_DOWN)
    status = "OK" if days > 0 else "NA"
    return {
        "account_id": a["account_id"],
        "value_date": BASE_DATE.isoformat(),
        "principal": a["principal"].quantize(Decimal("0.01")),
        "rate_bp": a["rate_bp"],
        "accrual_days": days,
        "interest": interest,
        "total": total,
        "status": status,
    }


def fmt(rec):
    """Dòng rộng cố định, đúng như báo cáo của một job theo lô thật."""
    return (
        f"{rec['account_id']:<10}"
        f"{rec['value_date']:<10}"
        f"{rec['principal']:>14}"
        f"{rec['rate_bp']:>6}"
        f"{rec['accrual_days']:>4}"
        f"{rec['interest']:>14}"
        f"{rec['total']:>14}"
        f"{rec['status']:>2}"
    )


def write(path, accounts, modern, stamp):
    rows = [compute(a, modern) for a in accounts]
    if modern:
        rows.sort(key=lambda r: r["account_id"])   # Khác biệt #2: thứ tự
    lines = [f"RUNSTAMP {stamp}"]                  # Khác biệt #3: dấu thời gian
    lines += [fmt(r) for r in rows]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return rows


def main():
    accounts = build_accounts()
    shuffled = accounts[:]
    random.shuffle(shuffled)   # hệ cũ ghi theo thứ tự xử lý, không sắp xếp

    old = write("legacy_output.txt", shuffled, modern=False, stamp="2026-11-09T23:14:07")
    new = write("modern_output.txt", accounts, modern=True, stamp="2026-11-10T02:41:55")

    by_id = {r["account_id"]: r for r in old}
    real_bugs = sum(
        1 for r in new if by_id[r["account_id"]]["accrual_days"] != r["accrual_days"]
    )
    rounding_only = sum(
        1 for r in new
        if by_id[r["account_id"]]["accrual_days"] == r["accrual_days"]
        and by_id[r["account_id"]]["interest"] != r["interest"]
    )

    print(f"Đã ghi legacy_output.txt và modern_output.txt — {N_ACCOUNTS} bản ghi.")
    print()
    print("Sự thật đã gieo vào (công cụ so sánh KHÔNG được biết trước):")
    print(f"  • sai nghiệp vụ thật (thừa một ngày lãi): {real_bugs} bản ghi")
    print(f"  • chỉ lệch do làm tròn:                   {rounding_only} bản ghi")
    print("  • toàn bộ 2.000 dòng lệch thứ tự, và dòng tiêu đề lệch dấu thời gian")


if __name__ == "__main__":
    main()
