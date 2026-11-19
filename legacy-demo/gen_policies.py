#!/usr/bin/env python3
"""Sinh tệp đầu vào `policies.dat`.

Đây là **dữ liệu đầu vào**, không phải dữ liệu kết quả — khác hẳn hai kịch bản
trong `spike/`. Ở đó script sinh ra cả hai tệp kết quả rồi tự gieo khác biệt vào;
ở đây nó chỉ sinh đầu vào, còn kết quả do hai chương trình độc lập tự tính ra.
Không ai biết trước chúng sẽ lệch ở đâu.

Dữ liệu được rải cố ý quanh các biên mà đặc tả im lặng: kỳ hạn đúng 365 ngày,
tiền gốc đúng 40.000,00, số kỳ bằng 1, hạng 3. Không phải để gieo lỗi — mà vì
một bộ dữ liệu không chạm biên nào thì không nói lên điều gì.

Chạy:  python3 gen_policies.py
"""

import random
import sys

# Windows mặc định ghi console bằng cp1252 và chết khi gặp tiếng Việt. Đúng lớp
# lỗi đã bắt được ngày 12/11 ở `verify.py`; tệp này bị bỏ sót lúc đó.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

N = 1200
SEED = 20261113
OUT = "policies.dat"


def main():
    rnd = random.Random(SEED)
    rows = []
    for i in range(N):
        pid = f"POL{i:07d}"
        start = f"2026{rnd.randrange(1, 13):02d}{rnd.randrange(1, 29):02d}"

        # Tiền gốc: rải rộng, nhưng nhồi thêm quanh đúng ngưỡng 40.000,00 để
        # chạm vào chỗ đặc tả không nói `>` hay `>=`.
        if rnd.random() < 0.06:
            cents = 4_000_000 + rnd.randrange(-3, 4)
        else:
            cents = rnd.randrange(50_000, 9_500_000)

        rate_bp = rnd.choice([250, 375, 500, 615, 750, 825, 1050])

        # Kỳ hạn: nhồi quanh 365 vì đó là chỗ áp trần.
        if rnd.random() < 0.12:
            term = 365 + rnd.randrange(-2, 3)
        else:
            term = rnd.randrange(30, 900)

        # Số kỳ: để 1 xuất hiện đủ nhiều, vì nó kích hoạt cả quy tắc `LS` lẫn
        # nhánh "kỳ cuối" mà đặc tả bỏ ngỏ.
        instal = rnd.choice([1, 1, 2, 3, 6, 12, 24])

        tier = rnd.choice("1123")

        rows.append(f"{pid:<10}{start}{cents:09d}{rate_bp:05d}"
                    f"{term:04d}{instal:02d}{tier}")

    with open(OUT, "w", encoding="ascii", newline="\n") as f:
        f.write("\n".join(rows) + "\n")

    print(f"Đã sinh {OUT}: {N} hợp đồng")
    print(f"  kỳ hạn chạm trần 365 : {sum(1 for r in rows if int(r[32:36]) >= 365)}")
    print(f"  tiền gốc quanh 40.000: {sum(1 for r in rows if abs(int(r[18:27]) - 4_000_000) <= 3)}")
    print(f"  trả một lần          : {sum(1 for r in rows if int(r[36:38]) == 1)}")
    print(f"  hạng 3               : {sum(1 for r in rows if r[38] == '3')}")


if __name__ == "__main__":
    main()
