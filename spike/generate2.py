#!/usr/bin/env python3
"""KỊCH BẢN 2 — dựng cặp tệp kết quả cho job xét duyệt yêu cầu bảo hiểm.

Cố tình khác hình dạng với kịch bản 1 để kiểm tra một điều duy nhất: luật phân
loại ở `classify.py` có phải sửa riêng cho bài toán này hay không.

Các khác biệt gieo vào bản "sau migration":

  A. Định dạng ngày đổi từ `2026-01-05` sang `05/01/2026`      — vô hại
  B. Tên nhà cung cấp bị chuẩn hoá: cắt khoảng trắng, đổi HOA  — vô hại
  C. `allowed` lệch trong phạm vi một xu (cắt số vs làm tròn)  — vô hại
  D. Dấu thời gian + số thứ tự lô ở dòng tiêu đề               — vô hại

  E. 3 dòng bị MẤT HẲN: điều kiện lọc `>` dịch nhầm thành `>=`  — CHẶN
  F. Mã `adjudication` sai trên các dòng bị từ chối một phần:
     hệ cũ ghi `PD` (partial deny), hệ mới ghi `DN` (deny)      — CHẶN

Lỗi F là loại lỗi migration tệ nhất ngoài đời: tiền vẫn đúng tới từng xu, chỉ
có *lý do* là sai. Không công cụ nào đối chiếu riêng cột tiền bắt được nó.
"""

import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

N = 1500
SEED = 20261110
BASE = date(2026, 1, 1)

PROVIDERS = [
    "Benh vien Da Nang", "Phong kham Hoan My", "Vinmec Da Nang",
    "Benh vien C", "Phong kham Pasteur", "Benh vien Gia Dinh",
]

# ─────────────────────────────────────────────────────────────────── sinh dữ liệu


def build_rows():
    rnd = random.Random(SEED)
    rows = []
    for i in range(N):
        claim = f"CLM{i // 3:06d}"
        line = i % 3 + 1
        svc = BASE + timedelta(days=rnd.randrange(300))
        provider = rnd.choice(PROVIDERS)
        billed = Decimal(rnd.randrange(20_000, 5_000_000)) / 100
        # Tỷ lệ chi trả theo hạng — chia 3 nên hầu như luôn ra số vô hạn tuần hoàn,
        # đó là nguồn của khác biệt cắt/làm tròn.
        tier = rnd.choice([1, 1, 1, 2, 2, 3])

        # Khám dự phòng được chi trả 100% → copay đúng bằng 0. Rất ít dòng, và
        # đó chính là nhóm bị điều kiện `>=` loại mất ở bản mới.
        preventive = rnd.random() < 0.004
        # Chia 3 nên hầu như luôn ra số vô hạn tuần hoàn — đó là nguồn của khác
        # biệt cắt-số / làm-tròn giữa hai hệ.
        ratio = Decimal(1) if preventive else Decimal(70 + tier * 5) / Decimal(300)

        allowed_exact = billed * ratio
        copay = (billed - allowed_exact).quantize(Decimal("0.01"), ROUND_HALF_UP)

        # Từ chối một phần: hạng cao nhất và vượt trần chi trả mỗi lần khám.
        partial = (tier == 3 and billed >= Decimal("45000.00"))
        rows.append({
            "claim_id": claim, "line_no": line, "service_date": svc,
            "provider": provider, "billed": billed,
            "allowed_exact": allowed_exact, "copay": copay,
            "tier": tier, "partial": partial,
        })
    return rows


def adjudication(r):
    if r["partial"]:
        return "PD"
    return "AP"


def deny_reason(r):
    return "RATE_TIER" if r["partial"] else ""


# ─────────────────────────────────────────────────────────────── ghi hai phiên bản


def write_legacy(rows, path):
    """Hệ cũ: ngày ISO, tên giữ nguyên như nhập, số bị CẮT, mã `PD` đúng."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("RUNSTAMP|2026-11-09T22:14:03|BATCH|000817\n")
        for r in rows:
            allowed = r["allowed_exact"].quantize(Decimal("0.01"), ROUND_DOWN)
            f.write("|".join([
                r["claim_id"], str(r["line_no"]),
                r["service_date"].isoformat(),
                f'  {r["provider"]} ',               # khoảng trắng như dữ liệu nhập
                f'{r["billed"]:.2f}', f"{allowed:.2f}", f'{r["copay"]:.2f}',
                str(r["tier"]), adjudication(r), deny_reason(r),
            ]) + "\n")


def write_modern(rows, path):
    """Hệ mới: ngày dd/mm/yyyy, tên chuẩn hoá, số LÀM TRÒN, và hai lỗi thật."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("RUNSTAMP|2026-11-10T06:02:51|BATCH|000818\n")
        dropped = 0
        for r in rows:
            # LỖI E — `>` dịch nhầm thành `>=`: dòng có copay đúng bằng 0 bị loại.
            if r["copay"] == 0:
                dropped += 1
                continue

            allowed = r["allowed_exact"].quantize(Decimal("0.01"), ROUND_HALF_UP)

            # LỖI F — gộp "từ chối một phần" vào "từ chối".
            adj = "DN" if r["partial"] else "AP"

            f.write("|".join([
                r["claim_id"], str(r["line_no"]),
                r["service_date"].strftime("%d/%m/%Y"),
                r["provider"].upper(),
                f'{r["billed"]:.2f}', f"{allowed:.2f}", f'{r["copay"]:.2f}',
                str(r["tier"]), adj, deny_reason(r),
            ]) + "\n")
    return dropped


if __name__ == "__main__":
    rows = build_rows()
    write_legacy(rows, "legacy2.txt")
    dropped = write_modern(rows, "modern2.txt")

    n_partial = sum(1 for r in rows if r["partial"])
    print(f"Đã dựng {N} dòng.")
    print(f"  Lỗi E — mất bản ghi do `>=`     : {dropped} dòng")
    print(f"  Lỗi F — mã PD bị ghi thành DN   : {n_partial} dòng")
    print(f"  Nhiễu  — đổi định dạng ngày     : {N} dòng")
    print(f"  Nhiễu  — chuẩn hoá tên          : {N} dòng")
