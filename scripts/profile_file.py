#!/usr/bin/env python3
"""Tệp lạ của khách  ->  `schema.json` nháp.

    python3 scripts/profile_file.py <tệp> [tệp-thứ-hai] [--name] [--out schema.json]

Đây là việc lặp lại duy nhất của nghề này: mỗi khách đưa một tệp có định dạng
riêng, và trước khi so sánh được gì thì phải khai được lược đồ. Làm tay mất nửa
ngày và dễ sai; làm bằng đếm thì vài giây và đúng.

**Phân công, và đây là điểm thiết kế quan trọng nhất của tệp này:**

  Phần xác định (tệp này)   : ranh giới cột, kiểu dữ liệu, scale thập phân,
                              khoá ứng viên, trường đổi theo lần chạy
  Mô hình ngôn ngữ (tuỳ chọn): CHỈ đặt tên cho cột

Suy kiểu bằng đếm thì đúng 100%; bằng mô hình ngôn ngữ thì không, và một lược đồ
sai kiểu sẽ âm thầm phân loại sai mọi khác biệt sau đó. Vì vậy mô hình không bao
giờ chạm vào con số — nó chỉ nhìn vài giá trị mẫu và đoán `account_id` thay vì
`field_03`.

**Mô hình phải chạy cục bộ.** Tệp này gọi Ollama hoặc LM Studio ở `localhost`, và
không có máy chủ nào thì nó vẫn ra lược đồ, chỉ là tên trường chung chung. Lý do
không phải tiết kiệm tiền: tệp kết quả batch của khách **không được rời khỏi mạng
của họ**. Gửi nó lên một API đám mây là phá đúng lời hứa đang dùng để bán hàng.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%m/%d/%Y", "%d-%m-%Y",
                "%Y/%m/%d", "%d.%m.%Y")
DELIMITERS = ("|", "\t", ";", ",")
HEADER_HINTS = ("RUNSTAMP", "HEADER", "HDR", "REPORT", "PAGE")
SAMPLE = 4000          # đủ để suy kiểu, không cần đọc hết tệp triệu dòng


# ───────────────────────────────────────────────────────── đọc và tách cột

def read_lines(path, limit=SAMPLE):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if line.strip():
                out.append(line)
            if len(out) >= limit:
                break
    return out


def split_header(lines):
    """Tách dòng tiêu đề ra khỏi bản ghi.

    Hai dấu hiệu: bắt đầu bằng từ khoá quen thuộc, hoặc có độ dài lệch hẳn so
    với phần còn lại. Dòng tiêu đề lọt vào tập bản ghi sẽ đẻ ra một "bản ghi mất"
    giả ở mọi lần chạy.
    """
    if not lines:
        return [], []
    common = Counter(len(l) for l in lines).most_common(1)[0][0]
    heads, recs = [], []
    for l in lines:
        hinted = any(l.upper().startswith(h) for h in HEADER_HINTS)
        odd = abs(len(l) - common) > max(4, common * 0.25)
        (heads if (hinted or odd) and len(heads) < 5 else recs).append(l)
    return heads, recs


def detect_delimiter(lines):
    """Ký tự phân tách, hoặc None nếu tệp là bề rộng cố định.

    Tiêu chí: xuất hiện ở hầu hết các dòng, và **số lần xuất hiện ổn định** —
    một dấu phẩy nằm trong tên khách hàng thì số lần sẽ nhảy lung tung.
    """
    for d in DELIMITERS:
        counts = [l.count(d) for l in lines]
        if not counts or min(counts) == 0:
            continue
        if len(set(counts)) == 1:
            return d
    return None


def fixed_boundaries(lines):
    """Ranh giới cột của tệp bề rộng cố định.

    Cột là khoảng chạy liên tục những vị trí **không phải lúc nào cũng trắng**.
    Vị trí nào trắng ở mọi dòng thì là khe ngăn cách.
    """
    width = max(len(l) for l in lines)
    padded = [l.ljust(width) for l in lines]
    blank = [all(p[i] == " " for p in padded) for i in range(width)]

    cols, start = [], None
    for i, b in enumerate(blank):
        if not b and start is None:
            start = i
        elif b and start is not None:
            cols.append((start, i - start))
            start = None
    if start is not None:
        cols.append((start, width - start))
    return cols


# ──────────────────────────────────────────────────────────── suy kiểu

INT_RE = re.compile(r"^[+-]?\d+$")
DEC_RE = re.compile(r"^[+-]?\d*[.,]\d+$")
# Một ngày nằm dính vào giữa hoặc cuối một chuỗi khác: dấu hiệu hai cột bị gộp.
MERGED_RE = re.compile(r".\d{4}-\d{2}-\d{2}|.\d{2}/\d{2}/\d{4}|\D\d{8}$")


def parse_date(v):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt), fmt
        except ValueError:
            continue
    return None, None


def infer(values):
    """(kiểu, scale, các định dạng ngày khớp) cho một cột."""
    vals = [v.strip() for v in values if v.strip()]
    if not vals:
        return "string", None, []

    if all(INT_RE.match(v) for v in vals):
        return "integer", None, []

    if all(INT_RE.match(v) or DEC_RE.match(v) for v in vals):
        scale = max((len(v.split(".")[-1].split(",")[-1])
                     for v in vals if not INT_RE.match(v)), default=0)
        return "decimal", scale, []

    # Ngày: chỉ nhận khi MỌI giá trị đọc được. Một cột gần-như-ngày mà khai là
    # ngày sẽ làm phần đọc tệp trả về chuỗi cho vài dòng, và phân loại sẽ lệch.
    matched = [set() for _ in vals]
    for i, v in enumerate(vals):
        for fmt in DATE_FORMATS:
            try:
                datetime.strptime(v, fmt)
                matched[i].add(fmt)
            except ValueError:
                pass
    common = set.intersection(*matched) if all(matched) else set()
    if common:
        return "date", None, sorted(common)

    return "string", None, []


def profile(path, second=None):
    lines = read_lines(path)
    if not lines:
        raise SystemExit(f"{path}: tệp rỗng")

    heads, recs = split_header(lines)
    delim = detect_delimiter(recs)

    if delim:
        rows = [r.split(delim) for r in recs]
        ncol = Counter(len(r) for r in rows).most_common(1)[0][0]
        rows = [r for r in rows if len(r) == ncol]
        layout = {"format": "delimited", "delimiter": delim}
        spans = None
    else:
        spans = fixed_boundaries(recs)
        rows = [[r[s:s + n] for s, n in spans] for r in recs]
        ncol = len(spans)
        layout = {"format": "fixed"}

    fields = []
    for i in range(ncol):
        col = [r[i] for r in rows]
        kind, scale, fmts = infer(col)
        f = {"name": f"field_{i:02d}", "type": kind}
        if spans:
            f["start"], f["len"] = spans[i]
        if scale:
            f["scale"] = scale
        if fmts and len(fmts) > 1:
            # Mơ hồ thật sự: `03/06/2026` khớp cả dd/mm lẫn mm/dd. Đoán bừa ở đây
            # là cách âm thầm bỏ qua một lỗi thật, nên phải bắt người khai chọn.
            f["formats"] = fmts
            f["_AMBIGUOUS"] = ("Khớp nhiều định dạng ngày. Hỏi khách rồi xoá "
                               "bớt, chỉ để lại một.")
        elif fmts:
            f["formats"] = fmts
        f["_sample"] = [v.strip() for v in col[:3]]
        f["_distinct"] = len({v.strip() for v in col})

        # Tệp bề rộng cố định không có dấu ngăn cách: hai trường sát nhau không
        # còn khoảng trắng nào ở giữa sẽ bị gộp thành một. Đây là giới hạn thật
        # của việc đoán ranh giới bằng cột trắng — phát hiện được thì phải nói,
        # vì một trường gộp làm hỏng cả khoá lẫn việc suy kiểu.
        if kind == "string" and MERGED_RE.search(f["_sample"][0] or ""):
            f["_MERGED"] = ("Có vẻ là hai trường bị gộp (không có khoảng trắng "
                            "ngăn cách). Cần copybook hoặc tài liệu định dạng "
                            "của khách để cắt đúng.")
        fields.append(f)

    n = len(rows)
    key = pick_key(fields, rows, n)
    volatile = pick_volatile(path, second, fields, rows, delim, spans)

    return {**layout, "key": key,
            "volatile": {"fields": volatile},
            "fields": fields,
            "_profiled": {"file": os.path.basename(path), "rows_sampled": n,
                          "header_lines": len(heads)}}


def pick_key(fields, rows, n):
    """Khoá ứng viên: cột duy nhất, hoặc cặp cột duy nhất.

    Không có khoá thì công cụ phải ghép theo số dòng, và lúc đó mọi khác biệt về
    thứ tự lại biến thành hàng nghìn khác biệt giả — đúng cái bệnh của `diff`.
    """
    single = [i for i, f in enumerate(fields)
              if f["_distinct"] == n and f["type"] != "decimal"]
    if single:
        return [fields[single[0]]["name"]]

    for i in range(len(fields)):
        for j in range(i + 1, len(fields)):
            if len({(r[i].strip(), r[j].strip()) for r in rows}) == n:
                return [fields[i]["name"], fields[j]["name"]]
    return []


def pick_volatile(path, second, fields, rows, delim, spans):
    """Trường đổi theo lần chạy.

    Chỉ kết luận được khi có **hai lần chạy của cùng một hệ thống**. Không có tệp
    thứ hai thì đoán theo hình dạng — và đoán thì phải nói là đoán.
    """
    if not second:
        return [f["name"] for f in fields
                if f["type"] == "date" and f["_distinct"] <= 2]

    other = read_lines(second)
    _, recs2 = split_header(other)
    rows2 = ([r.split(delim) for r in recs2] if delim
             else [[r[s:s + n] for s, n in spans] for r in recs2])
    rows2 = [r for r in rows2 if len(r) == len(fields)]

    out = []
    for i, f in enumerate(fields):
        a = [r[i].strip() for r in rows]
        b = [r[i].strip() for r in rows2[:len(a)]]
        if b and a != b and all(x != y for x, y in zip(a, b)):
            out.append(f["name"])      # đổi ở MỌI dòng -> theo lần chạy

    # Nếu quá nửa số cột "đổi theo lần chạy" thì giả thiết đã sai: hai tệp này
    # không phải hai lần chạy của cùng một hệ thống — nhiều khả năng là bản cũ
    # so với bản mới, hoặc bản mới đã sắp xếp lại thứ tự dòng. Khai nhầm một cột
    # là volatile nghĩa là **vĩnh viễn không bao giờ kiểm tra cột đó nữa**, nên
    # thà trả về rỗng còn hơn trả về một lược đồ mù.
    if len(out) > len(fields) / 2:
        return []
    return out


# ──────────────────────────────────────── đặt tên bằng mô hình chạy cục bộ

LOCAL_ENDPOINTS = [
    ("Ollama", "http://localhost:11434/v1/chat/completions"),
    ("LM Studio", "http://localhost:1234/v1/chat/completions"),
    ("llama.cpp", "http://localhost:8080/v1/chat/completions"),
]


def local_chat(prompt, model=None, timeout=90):
    """Gọi một máy chủ tương thích OpenAI đang chạy ở localhost. None nếu không có.

    Chỉ `localhost`. Không có đường nào trong tệp này gửi dữ liệu ra ngoài máy,
    và đó là một ràng buộc của sản phẩm chứ không phải một tuỳ chọn.
    """
    import urllib.error
    import urllib.request

    body = {"messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "stream": False}
    if model:
        body["model"] = model

    for name, url in LOCAL_ENDPOINTS:
        try:
            req = urllib.request.Request(
                url, data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            return name, data["choices"][0]["message"]["content"]
        except Exception:
            continue
    return None, None


def name_fields(schema, model=None):
    """Nhờ mô hình cục bộ đặt tên. Thất bại thì giữ nguyên `field_NN`."""
    cols = [{"i": i, "type": f["type"], "sample": f["_sample"],
             "distinct": f["_distinct"]}
            for i, f in enumerate(schema["fields"])]

    prompt = (
        "You are naming columns of a batch job output file from a legacy "
        "business system. For each column below, give a short snake_case "
        "field name based on the sample values and type.\n\n"
        "Rules: names only, no explanation. Do not change the order. Do not "
        "invent types. Reply with a JSON array of strings and nothing else.\n\n"
        + json.dumps(cols, ensure_ascii=False, indent=1))

    who, reply = local_chat(prompt, model)
    if not reply:
        return False, ("Không thấy mô hình cục bộ nào ở localhost "
                       "(Ollama 11434 / LM Studio 1234 / llama.cpp 8080).")

    m = re.search(r"\[.*\]", reply, re.S)
    if not m:
        return False, f"{who} trả lời không phải JSON — giữ nguyên tên cũ."
    try:
        names = json.loads(m.group(0))
    except json.JSONDecodeError:
        return False, f"{who} trả JSON hỏng — giữ nguyên tên cũ."

    if len(names) != len(schema["fields"]):
        return False, (f"{who} trả {len(names)} tên cho "
                       f"{len(schema['fields'])} cột — không khớp, bỏ qua.")

    seen = Counter()
    for f, raw in zip(schema["fields"], names):
        nm = re.sub(r"[^a-z0-9_]", "_", str(raw).strip().lower()).strip("_")
        if not nm:
            continue
        seen[nm] += 1
        f["name"] = nm if seen[nm] == 1 else f"{nm}_{seen[nm]}"

    # Khoá và trường volatile tham chiếu theo tên, nên phải đổi theo.
    idx = {f"field_{i:02d}": f["name"] for i, f in enumerate(schema["fields"])}
    schema["key"] = [idx.get(k, k) for k in schema["key"]]
    schema["volatile"]["fields"] = [idx.get(k, k)
                                    for k in schema["volatile"]["fields"]]
    return True, f"Đã đặt tên bằng {who} (chạy cục bộ)."


# ───────────────────────────────────────────────────────────────── chạy

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("second", nargs="?",
                    help="lần chạy thứ hai của CÙNG hệ thống — để tìm trường "
                         "đổi theo lần chạy")
    ap.add_argument("--name", action="store_true",
                    help="nhờ mô hình cục bộ đặt tên cột")
    ap.add_argument("--model", help="tên model cho máy chủ cục bộ")
    ap.add_argument("--out", help="ghi ra tệp thay vì in ra màn hình")
    args = ap.parse_args()

    schema = profile(args.file, args.second)

    note = None
    if args.name:
        ok, note = name_fields(schema, args.model)

    text = json.dumps(schema, ensure_ascii=False, indent=2)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text + "\n")
        print(f"ghi {args.out}")
    else:
        print(text)

    # Mọi cảnh báo ra stderr, để `--out` không có cũng pipe được sang tệp.
    w = sys.stderr
    if note:
        print(f"\n{note}", file=w)
    if not schema["key"]:
        print("\nCẢNH BÁO: không tìm được khoá duy nhất. Không có khoá thì phải "
              "ghép theo số dòng, và đảo thứ tự sẽ thành hàng nghìn khác biệt "
              "giả. Hỏi khách xem tổ hợp trường nào định danh một bản ghi.",
              file=w)
    if not args.second:
        print("\nLƯU Ý: chỉ có một tệp, nên trường 'đổi theo lần chạy' là PHỎNG "
              "ĐOÁN. Xin thêm một lần chạy nữa của hệ CŨ rồi chạy lại với cả hai "
              "tệp.", file=w)
    for f in schema["fields"]:
        if "_AMBIGUOUS" in f:
            print(f"\nCẦN HỎI KHÁCH: `{f['name']}` khớp nhiều định dạng ngày "
                  f"({', '.join(f['formats'])}). Đoán sai ở đây là âm thầm bỏ "
                  f"qua lỗi thật.", file=w)
        if "_MERGED" in f:
            print(f"\nCẦN HỎI KHÁCH: `{f['name']}` (vị trí {f.get('start')}, "
                  f"dài {f.get('len')}) có vẻ là HAI trường bị gộp — mẫu: "
                  f"{f['_sample'][0]!r}. Xin copybook hoặc bản mô tả định dạng.",
                  file=w)
    if args.second and not schema["volatile"]["fields"]:
        print("\nLƯU Ý: không kết luận được trường nào đổi theo lần chạy. Nếu "
              "tệp thứ hai là bản SAU migration thì đó là sai cách dùng — cần "
              "hai lần chạy của cùng hệ CŨ.", file=w)

    print("\nTrước khi dùng: xoá các khoá `_sample`, `_distinct`, `_profiled`, "
          "`_AMBIGUOUS` và kiểm tra lại từng tên trường với khách.", file=w)


if __name__ == "__main__":
    main()
