#!/usr/bin/env python3
"""Bộ kiểm thử. Không pytest, không phụ thuộc ngoài.

Chạy:  python3 tests/run.py

Lý do viết tay thay vì dùng pytest: công cụ này được bán cho ngân hàng, và một
`pip install` là một cuộc họp với bộ phận bảo mật. Bộ test chạy được bằng
`python3 tests/run.py` trên một máy không có mạng là một tính năng, không phải
sự cố chấp.
"""

import os
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# `tests/mutate.py` trỏ biến này vào một bản sao đã bị cố ý phá, rồi đòi bộ test
# phải đỏ. Nếu không có nó thì không có cách nào kiểm tra bộ test biết fail.
SPIKE = os.environ.get("SPIKE_DIR") or os.path.join(ROOT, "spike")
sys.path.insert(0, SPIKE)

import classify as C          # noqa: E402
import records as R           # noqa: E402
import report as REP          # noqa: E402

PASS = FAIL = 0
FAILURES = []


def check(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(label)


def eq(got, want, label):
    check(got == want, f"{label}: nhận {got!r}, cần {want!r}")


# ───────────────────────────────────────────────────── lược đồ dùng cho test

FIELDS = [
    {"name": "id",      "type": "string",  "start": 0,  "len": 6},
    {"name": "day",     "type": "date",    "start": 6,  "len": 10},
    {"name": "count",   "type": "integer", "start": 16, "len": 4},
    {"name": "amount",  "type": "decimal", "start": 20, "len": 10, "scale": 2},
    {"name": "stamp",   "type": "string",  "start": 30, "len": 8},
]
SCHEMA = {"format": "fixed", "key": ["id"], "fields": FIELDS,
          "volatile_fields": {"stamp"}}

F = {f["name"]: f for f in FIELDS}


def kind(name, old, new):
    v = C.classify_field(name, old, new, F[name], SCHEMA)
    return None if v is None else v[0]


# ───────────────────────────────────────────────────────── 1. phân loại

def test_classify():
    eq(kind("amount", Decimal("10.00"), Decimal("10.00")), None,
       "bằng nhau thì không phải khác biệt")

    # Trường khai là đổi mỗi lần chạy — không bao giờ chặn.
    eq(kind("stamp", "0830", "0912"), C.VOLATILE, "trường volatile bị bỏ qua")

    # Dung sai thập phân: đúng một đơn vị là làm tròn, hơn một chút là nghiệp vụ.
    eq(kind("amount", Decimal("10.00"), Decimal("10.01")), C.ROUNDING,
       "lệch đúng 1 đơn vị = làm tròn")
    eq(kind("amount", Decimal("10.00"), Decimal("9.99")), C.ROUNDING,
       "lệch 1 đơn vị theo chiều âm = làm tròn")
    eq(kind("amount", Decimal("10.00"), Decimal("10.02")), C.BUSINESS,
       "lệch 2 đơn vị = sai nghiệp vụ")

    # ĐÂY LÀ LUẬT QUAN TRỌNG NHẤT CỦA CẢ SẢN PHẨM.
    # Số nguyên không có dung sai. Nếu test này đỏ thì lý do tồn tại của công cụ
    # đã mất, bất kể các test khác xanh thế nào.
    eq(kind("count", 365, 366), C.BUSINESS, "số nguyên lệch 1 = sai nghiệp vụ")
    eq(kind("count", 0, 1), C.BUSINESS, "số nguyên lệch 1 từ 0 = sai nghiệp vụ")

    # Chuỗi: khác cách viết thì báo nhưng không chặn; khác giá trị thì chặn.
    eq(kind("id", "AB01", "ab01 "), C.FORMATTING, "khác hoa/thường + khoảng trắng")
    eq(kind("id", " AB01", "AB01"), C.FORMATTING, "khác khoảng trắng đầu")
    eq(kind("id", "AB01", "AB02"), C.BUSINESS, "chuỗi khác giá trị = sai nghiệp vụ")

    # FORMATTING không được nằm trong nhóm chặn, BUSINESS thì phải.
    check(C.FORMATTING not in C.BLOCKING, "FORMATTING không chặn")
    check(C.VOLATILE not in C.BLOCKING, "VOLATILE không chặn")
    check(C.ROUNDING not in C.BLOCKING, "ROUNDING không chặn")
    check(C.BUSINESS in C.BLOCKING, "BUSINESS phải chặn")
    check(C.MISSING in C.BLOCKING, "MISSING phải chặn")
    check(C.EXTRA in C.BLOCKING, "EXTRA phải chặn")

    # Dung sai phải theo scale khai trong lược đồ, không phải hằng số 0.01.
    f4 = {"name": "rate", "type": "decimal", "scale": 4}
    s = {"volatile_fields": set()}
    eq(C.classify_field("rate", Decimal("1.0000"), Decimal("1.0001"), f4, s)[0],
       C.ROUNDING, "scale 4: lệch 0.0001 = làm tròn")
    eq(C.classify_field("rate", Decimal("1.0000"), Decimal("1.0002"), f4, s)[0],
       C.BUSINESS, "scale 4: lệch 0.0002 = sai nghiệp vụ")

    # Lược đồ quên khai scale thì mặc định là 2 chữ số thập phân — mức của tiền.
    # Mặc định im lặng là thứ nguy hiểm, nên nó phải được canh bằng test.
    f0 = {"name": "amt", "type": "decimal"}
    eq(C.classify_field("amt", Decimal("1.00"), Decimal("1.01"), f0, s)[0],
       C.ROUNDING, "không khai scale: mặc định 2, lệch 0.01 = làm tròn")
    eq(C.classify_field("amt", Decimal("1.00"), Decimal("1.02"), f0, s)[0],
       C.BUSINESS, "không khai scale: lệch 0.02 = sai nghiệp vụ")

    # Trường khai là decimal nhưng giá trị không đọc được thành số (rác trong
    # tệp, trường bị lệch cột). Không được vỡ, và không được âm thầm cho qua.
    eq(C.classify_field("amt", "12.00", Decimal("12.50"), f0, s)[0], C.BUSINESS,
       "decimal nhưng một bên là rác: vẫn chặn, không vỡ")
    eq(C.classify_field("amt", "ABC", "XYZ", f0, s)[0], C.BUSINESS,
       "decimal nhưng cả hai bên là rác: vẫn chặn")

    # Ghi chú của trường số nguyên phải nói rõ lệch bao nhiêu — đó là bằng chứng
    # người duyệt nhìn vào, không phải chỉ cái nhãn BUSINESS.
    eq(C.classify_field("count", 365, 366, F["count"], SCHEMA)[1],
       "integer off by 1", "ghi chú số nguyên nêu rõ độ lệch")

    # Nhánh chuỗi không được nuốt giá trị không phải chuỗi (ví dụ hai `date`
    # khác nhau lọt vào trường khai kiểu khác).
    import datetime as _dt
    fd = {"name": "day", "type": "date"}
    eq(C.classify_field("day", _dt.date(2026, 1, 1), _dt.date(2026, 1, 2), fd, s)[0],
       C.BUSINESS, "hai ngày khác nhau = sai nghiệp vụ")
    eq(C.classify_field("day", _dt.date(2026, 1, 1), "2026-01-02", fd, s)[0],
       C.BUSINESS, "ngày so với chuỗi: vẫn chặn, không vỡ")


# ─────────────────────────────────────────────── 2. đọc tệp và ghép bản ghi

def test_records():
    # Ngày: hai cách viết của cùng một ngày KHÔNG phải hai giá trị lệch.
    d1 = R._coerce("2026-06-03", F["day"])
    d2 = R._coerce("03/06/2026", F["day"])
    eq(d1, d2, "2026-06-03 và 03/06/2026 là cùng một ngày")
    check(d1 is not None and not isinstance(d1, str), "ngày phải được đọc thành date")

    # Lược đồ khai formats riêng thì phải tôn trọng, không đoán.
    us = {"name": "day", "type": "date", "formats": ["%m/%d/%Y"]}
    eq(R._coerce("03/06/2026", us).month, 3, "khai %m/%d/%Y thì 03/06 là tháng 3")

    eq(R._coerce("  42  ", F["count"]), 42, "số nguyên bỏ khoảng trắng")
    eq(R._coerce("", F["count"]), None, "rỗng thành None")
    eq(R._coerce("12.30", F["amount"]), Decimal("12.30"), "thập phân giữ scale")

    # Ghép theo khoá: đảo thứ tự KHÔNG được tính là khác biệt.
    a = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    b = [{"id": "C"}, {"id": "A"}, {"id": "B"}]
    sch = {"key": ["id"]}
    pairs, only_a, only_b, reordered = R.align(a, b, sch)
    eq(len(pairs), 3, "ghép đủ 3 cặp dù đảo thứ tự")
    eq(only_a, [], "không bản ghi nào chỉ có bên trái")
    eq(only_b, [], "không bản ghi nào chỉ có bên phải")
    check(reordered, "phải nhận ra thứ tự đã đổi")

    # Bản ghi mất và thừa.
    pairs, only_a, only_b, _ = R.align([{"id": "A"}, {"id": "B"}],
                                       [{"id": "B"}, {"id": "Z"}], sch)
    eq([k[0] for k in only_a], ["A"], "A mất ở bản mới")
    eq([k[0] for k in only_b], ["Z"], "Z thừa ở bản mới")

    # Khoá ghép nhiều trường.
    two = {"key": ["id", "count"]}
    eq(R.key_of({"id": "A", "count": 2}, two), ("A", "2"), "khoá hai trường")

    # Tệp phân tách: thiếu trường ở cuối dòng phải được đệm, không được vỡ.
    dsch = {"format": "delimited", "delimiter": "|",
            "fields": [{"name": "a", "type": "string"},
                       {"name": "b", "type": "string"},
                       {"name": "c", "type": "string"}]}
    eq(R._split_delimited("x|y", dsch), ["x", "y", ""], "đệm trường thiếu")
    eq(R._split_delimited("x|y|z|w", dsch), ["x", "y", "z"], "cắt trường thừa")

    # Dòng trống trong tệp không được biến thành một bản ghi rỗng. Một job batch
    # kết thúc bằng dòng trống là chuyện bình thường, và nếu nó thành bản ghi thì
    # báo cáo sẽ có một "bản ghi mất" giả ở mọi lần chạy.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "f.txt")
        open(p, "w", encoding="utf-8").write("A|1|x\n\n   \nB|2|y\n")
        recs, heads = R.parse(p, dsch)
        eq(len(recs), 2, "dòng trống bị bỏ qua, không thành bản ghi")
        eq(heads, [], "không có dòng tiêu đề")

        # Dòng tiêu đề phải tách khỏi bản ghi, không bị đem đi ghép theo khoá.
        p2 = os.path.join(tmp, "g.txt")
        open(p2, "w", encoding="utf-8").write("RUNSTAMP|2026-01-01\nA|1|x\n")
        recs, heads = R.parse(p2, dsch)
        eq(len(recs), 1, "dòng RUNSTAMP không phải bản ghi")
        eq(len(heads), 1, "dòng RUNSTAMP được giữ làm tiêu đề")


# ───────────────────────────────────────────────────────────── 3. báo cáo

def test_report():
    clean = REP.render([], 10, False, False, lang="en")
    check("SHIP" in clean and "DO NOT" not in clean, "không khác biệt thì ĐẠT")

    bad = [{"key": ("A",), "field": "count", "kind": C.BUSINESS,
            "old": 1, "new": 2, "note": "integer off by 1"}]
    out = REP.render(bad, 10, False, False, lang="en")
    check("DO NOT SHIP" in out, "có sai nghiệp vụ thì KHÔNG ĐẠT")
    check("count" in out, "báo cáo nêu tên trường")

    # Khác biệt không chặn không được làm báo cáo chuyển sang KHÔNG ĐẠT.
    soft = [{"key": ("A",), "field": "amount", "kind": C.ROUNDING,
             "old": 1, "new": 1, "note": "x"},
            {"key": ("A",), "field": "name", "kind": C.FORMATTING,
             "old": "a", "new": "A", "note": "x"}]
    out = REP.render(soft, 10, False, False, lang="en")
    check("SHIP" in out and "DO NOT SHIP" not in out,
          "chỉ làm tròn và cách viết thì vẫn ĐẠT")

    # Hai ngôn ngữ phải cùng kết luận.
    vi = REP.render(bad, 10, False, False, lang="vi")
    check("KHÔNG ĐẠT" in vi, "bản tiếng Việt cùng kết luận")

    # Khoá nhiều trường phải in đủ, không chỉ trường đầu.
    multi = [{"key": ("CLM1", "2"), "field": "code", "kind": C.BUSINESS,
              "old": "PD", "new": "DN", "note": "x"}]
    check("CLM1/2" in REP.render(multi, 1, False, False, lang="en"),
          "in đủ khoá ghép nhiều trường")

    # Báo cáo chỉ in `sample` ví dụ rồi tóm tắt phần còn lại. Nếu phần "còn N chỗ
    # nữa" biến mất thì người đọc tưởng đã thấy hết — nguy hiểm hơn là dài dòng.
    many = [{"key": (f"K{i}",), "field": "f", "kind": C.BUSINESS,
             "old": 1, "new": 2, "note": "n"} for i in range(9)]
    out = REP.render(many, 9, False, False, sample=3, lang="en")
    eq(out.count("K0") + out.count("K1") + out.count("K2"), 3,
       "in đúng `sample` ví dụ")
    check("6 more" in out, "nêu số chỗ còn lại")
    check("K8" not in out, "không in quá `sample` ví dụ")
    # Đúng bằng `sample` thì không được in dòng "còn ... nữa".
    exact = REP.render(many[:3], 3, False, False, sample=3, lang="en")
    check("more" not in exact, "đúng bằng sample thì không có dòng 'còn lại'")
    # Mặc định `sample` phải là 6 — nó quyết định báo cáo dài bao nhiêu.
    six = REP.render(many, 9, False, False, lang="en")
    check("3 more" in six, "mặc định sample = 6")

    # Khối "cần ký duyệt" là nơi duy nhất báo cho người duyệt biết sổ sách có
    # thay đổi thật. Mất khối này là báo cáo ĐẠT mà giấu thông tin.
    rnd = [{"key": ("A",), "field": "amount", "kind": C.ROUNDING,
            "old": 1, "new": 1, "note": "x"}]
    out = REP.render(rnd, 1, False, False, lang="en")
    check("sign-off" in out, "có làm tròn thì phải có khối ký duyệt")
    check("1 field" in out or "1 fields" in out, "khối ký duyệt nêu số lượng")
    check("sign-off" not in REP.render([], 1, False, False, lang="en"),
          "không làm tròn thì không có khối ký duyệt")

    # Dòng tiêu đề đổi hay không là hai thông tin khác nhau, không được lẫn.
    check("Header line      : changed" in REP.render([], 1, False, True, lang="en"),
          "tiêu đề đổi được báo đúng")
    check("Header line      : identical" in REP.render([], 1, False, False, lang="en"),
          "tiêu đề không đổi được báo đúng")


# ──────────────────────────────────────────── 4. chạy thật cả hai kịch bản

def run_scenario(gen, old, new, schema):
    import subprocess
    subprocess.run([sys.executable, gen], cwd=SPIKE, capture_output=True, check=True)
    p = subprocess.run([sys.executable, "verify.py", old, new, schema, "--lang=en"],
                       cwd=SPIKE, capture_output=True, text=True)
    return p.returncode, p.stdout


def test_end_to_end():
    # Kịch bản 1 — lỗi nằm ở số tiền. Đúng 4 bản ghi, 12 khác biệt.
    code, out = run_scenario("generate.py", "legacy_output.txt",
                             "modern_output.txt", "schema.json")
    eq(code, 1, "kịch bản 1 phải trả mã thoát 1")
    check("across 4 records" in out, "kịch bản 1 tìm đúng 4 bản ghi")
    check("accrual_days" in out, "kịch bản 1 nêu trường nguyên nhân")
    check("Record order     : changed" in out,
          "kịch bản 1: đảo thứ tự được nhận ra và không bị tính là lệch")

    # Kịch bản 2 — lỗi nằm ở mã trạng thái, cộng bản ghi bị mất.
    code, out = run_scenario("generate2.py", "legacy2.txt",
                             "modern2.txt", "schema2.json")
    eq(code, 1, "kịch bản 2 phải trả mã thoát 1")
    check("across 25 records" in out, "kịch bản 2 tìm đúng 25 bản ghi")
    check("RECORDS MISSING" in out, "kịch bản 2 phát hiện bản ghi mất")
    check("adjudication" in out, "kịch bản 2 nêu trường mã trạng thái")
    # 1.490 dòng đổi định dạng ngày và đổi HOA KHÔNG được thành báo nhầm.
    check("service_date" not in out.split("Acceptable")[0],
          "đổi định dạng ngày không bị báo là sai nghiệp vụ")
    check("provider" not in out.split("Acceptable")[0],
          "đổi hoa/thường không bị báo là sai nghiệp vụ")

    # Một tệp so với chính nó thì phải ĐẠT và trả mã thoát 0.
    import subprocess
    p = subprocess.run([sys.executable, "verify.py", "legacy2.txt",
                        "legacy2.txt", "schema2.json", "--lang=en"],
                       cwd=SPIKE, capture_output=True, text=True)
    eq(p.returncode, 0, "tệp so với chính nó: mã thoát 0")
    check("SHIP" in p.stdout and "DO NOT" not in p.stdout,
          "tệp so với chính nó: ĐẠT")


# ────────────────────────────────────────────────── 5. hợp đồng dòng lệnh

def cli(*argv):
    """Chạy verify.py và trả về (mã thoát, đầu ra)."""
    import subprocess
    p = subprocess.run([sys.executable, "verify.py", *argv],
                       cwd=SPIKE, capture_output=True, text=True)
    return p.returncode, p.stdout


def test_cli():
    """Mã thoát là hợp đồng với CI của khách. Sai mã thoát = cổng chặn không chặn."""
    import subprocess
    subprocess.run([sys.executable, "generate2.py"], cwd=SPIKE,
                   capture_output=True, check=True)

    # Thiếu hoặc thừa tham số: mã thoát 2 (lỗi dùng sai), KHÔNG phải 0 hay 1.
    # Nhầm sang 0 là thảm hoạ: pipeline xanh vì công cụ còn chưa chạy.
    for bad in ([], ["a"], ["a", "b"], ["a", "b", "c", "d"]):
        code, out = cli(*bad)
        eq(code, 2, f"dùng sai tham số ({len(bad)} tham số) phải trả mã 2")
    check("usage" in out.lower() or "Chạy:" in out, "dùng sai thì in hướng dẫn")

    # Cờ không được tính là tham số vị trí.
    code, _ = cli("legacy2.txt", "modern2.txt", "schema2.json", "--lang=en")
    eq(code, 1, "có cờ --lang vẫn nhận đủ 3 tham số")

    # Cờ đặt ở đâu cũng phải ăn. Người ta gõ `verify.py --lang=en a b c` nhiều
    # không kém `verify.py a b c --lang=en`, và im lặng ra sai ngôn ngữ thì khó
    # nhận ra hơn là báo lỗi.
    _, first = cli("--lang=en", "legacy2.txt", "modern2.txt", "schema2.json")
    check("DO NOT SHIP" in first, "cờ đặt trước tham số vẫn ăn")

    # Cờ chọn ngôn ngữ phải thật sự đổi ngôn ngữ, cả hai chiều.
    _, en = cli("legacy2.txt", "modern2.txt", "schema2.json", "--lang=en")
    _, vi = cli("legacy2.txt", "modern2.txt", "schema2.json")
    check("DO NOT SHIP" in en and "KHÔNG ĐẠT" not in en, "--lang=en ra tiếng Anh")
    check("KHÔNG ĐẠT" in vi and "DO NOT SHIP" not in vi, "mặc định ra tiếng Việt")

    # Tiêu đề: hai tệp khác dấu thời gian ở dòng RUNSTAMP phải được báo là đổi,
    # còn tệp so với chính nó thì không.
    _, diff_head = cli("legacy2.txt", "modern2.txt", "schema2.json", "--lang=en")
    check("Header line      : changed" in diff_head, "tiêu đề khác được báo")
    _, same_head = cli("legacy2.txt", "legacy2.txt", "schema2.json", "--lang=en")
    check("Header line      : identical" in same_head, "tiêu đề giống được báo")


# ───────────────────────────────────────────────── 6. bộ dựng lược đồ nháp

def test_profiler():
    """`profile_file.py` phải suy ra đúng lược đồ kịch bản 2 mà không được mách.

    Đây là bài kiểm tra có đáp án: `schema2.json` là sự thật, và bộ dựng lược đồ
    chỉ nhìn tệp dữ liệu. Nếu nó suy sai kiểu hoặc sai khoá thì mọi phân loại
    phía sau đều sai theo, và người dùng sẽ không bao giờ biết.
    """
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import subprocess
    subprocess.run([sys.executable, "generate2.py"], cwd=SPIKE,
                   capture_output=True, check=True)
    import profile_file as P

    got = P.profile(os.path.join(SPIKE, "legacy2.txt"))
    want = __import__("json").load(
        open(os.path.join(SPIKE, "schema2.json"), encoding="utf-8"))

    eq(got["format"], "delimited", "nhận ra tệp phân tách")
    eq(got["delimiter"], "|", "nhận ra ký tự phân tách")
    eq(len(got["fields"]), len(want["fields"]), "đúng số cột")

    # Khoá: phải ra đúng cặp (claim_id, line_no) — cột 0 và 1.
    eq(got["key"], ["field_00", "field_01"], "tìm đúng khoá ghép hai trường")

    for i, (g, w) in enumerate(zip(got["fields"], want["fields"])):
        eq(g["type"], w["type"], f"cột {i} ({w['name']}): đúng kiểu")
        if w.get("scale"):
            eq(g.get("scale"), w["scale"], f"cột {i} ({w['name']}): đúng scale")

    # Ngày phải ra đúng một định dạng, không mơ hồ — tệp này dùng ISO.
    day = got["fields"][2]
    eq(day["formats"], ["%Y-%m-%d"], "nhận đúng định dạng ngày ISO")
    check("_AMBIGUOUS" not in day, "ngày ISO không mơ hồ")

    # Ngày kiểu 03/06/2026 thì MƠ HỒ và phải được đánh dấu, không được đoán.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "amb.txt")
        open(p, "w", encoding="utf-8").write(
            "A|03/06/2026|1\nB|04/07/2026|2\nC|05/08/2026|3\n")
        s = P.profile(p)
        check("_AMBIGUOUS" in s["fields"][1],
              "ngày khớp cả dd/mm lẫn mm/dd phải bị đánh dấu mơ hồ")

        # Hai tệp không phải hai lần chạy cùng hệ: thà trả rỗng còn hơn khai
        # bừa, vì khai nhầm volatile là vĩnh viễn thôi kiểm tra cột đó.
        q = os.path.join(tmp, "other.txt")
        open(q, "w", encoding="utf-8").write(
            "Z|09/09/2026|9\nY|08/08/2026|8\nX|07/07/2026|7\n")
        eq(P.profile(p, q)["volatile"]["fields"], [],
           "quá nửa số cột 'đổi mỗi lần chạy' thì từ chối kết luận")

    # Không có mô hình cục bộ thì vẫn phải ra lược đồ, chỉ là tên chung chung.
    ok, note = P.name_fields({"fields": [{"name": "field_00", "type": "string",
                                          "_sample": ["x"], "_distinct": 1}],
                              "key": [], "volatile": {"fields": []}})
    check(ok is False or isinstance(note, str),
          "không có mô hình cục bộ thì báo rõ, không vỡ")


# ──────────────────────────────────────────────────────── 7. ranh giới kiến trúc

def test_boundaries():
    """CLAUDE.md tuyên bố hai ranh giới. Tuyên bố không được kiểm tra thì sẽ trôi."""
    src = open(os.path.join(SPIKE, "classify.py"), encoding="utf-8").read()

    check("import records" not in src and "from records" not in src,
          "classify.py không được phụ thuộc đường ống")
    check("import report" not in src and "from report" not in src,
          "classify.py không được phụ thuộc báo cáo")

    # Không có nghiệp vụ của khách trong luật phân loại. Đây là ranh giới
    # sản-phẩm / tư-vấn, và nó phải được máy canh chứ không canh bằng trí nhớ.
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for word in ("interest", "lãi", "account", "insurance", "bảo hiểm",
                 "claim", "policy", "tài khoản"):
        check(word.lower() not in code.lower(),
              f"classify.py không được nhắc nghiệp vụ: `{word}`")


if __name__ == "__main__":
    for t in (test_classify, test_records, test_report,
              test_end_to_end, test_cli, test_profiler, test_boundaries):
        t()
    print(f"{PASS} đạt, {FAIL} hỏng")
    for m in FAILURES:
        print("  HỎNG:", m)
    sys.exit(1 if FAIL else 0)
