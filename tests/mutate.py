#!/usr/bin/env python3
"""Bộ kiểm thử của bộ kiểm thử.

    python3 tests/mutate.py            # chạy tất cả
    python3 tests/mutate.py -v         # in từng đột biến
    python3 tests/mutate.py --only classify.py

Ý tưởng: lấy mã nguồn, **cố ý phá một chỗ**, rồi chạy `tests/run.py`. Nếu bộ test
vẫn xanh thì đột biến đó **sống sót** — nghĩa là có một hành vi của sản phẩm mà
không test nào canh. Mỗi đột biến sống sót là một lỗ thủng có địa chỉ cụ thể.

Vì sao việc này quan trọng hơn ở đây so với ở dự án khác: **sản phẩm này chính là
một bộ kiểm thử.** Khách trả tiền để nghe câu "không có gì sai". Một công cụ không
chứng minh được là nó biết nói "có cái sai" thì câu trả lời của nó vô nghĩa. Đây là
thứ đưa ra khi khách hỏi *"sao tôi tin được báo cáo của anh?"*.

Không phụ thuộc ngoài. Chỉ dùng `ast` của thư viện chuẩn.
"""

import argparse
import ast
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPIKE = os.path.join(ROOT, "spike")
RUNNER = os.path.join(ROOT, "tests", "run.py")

# Chỉ đột biến mã sản phẩm. `generate*.py` là dữ liệu thử, `make_gallery.py` là
# tài sản bán hàng — phá chúng không nói lên điều gì về chất lượng bộ test.
TARGETS = ["classify.py", "records.py", "report.py", "verify.py"]

CMP_SWAP = {
    ast.LtE: ast.Lt, ast.Lt: ast.LtE,
    ast.GtE: ast.Gt, ast.Gt: ast.GtE,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}


# ─────────────────────────────────────────────────────────── sinh đột biến

class Mutator(ast.NodeTransformer):
    """Đếm các vị trí có thể đột biến, và khi được chỉ định thì sửa đúng một vị trí."""

    def __init__(self, target=None):
        self.sites = []          # (mô tả, dòng)
        self.target = target     # chỉ số vị trí cần sửa, None = chỉ đếm
        self.i = -1

    def _hit(self, desc, node):
        self.i += 1
        if self.target is None:
            self.sites.append((desc, getattr(node, "lineno", 0)))
        return self.i == self.target

    # so sánh:  <=  thành  <  v.v.
    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in CMP_SWAP:
            old = type(node.ops[0])
            new = CMP_SWAP[old]
            if self._hit(f"so sánh {old.__name__} -> {new.__name__}", node):
                node.ops = [new()]
        return node

    # Bề rộng đường kẻ (`"=" * 70`) là trình bày, không phải hành vi. Đột biến ở
    # đó luôn sống sót, và đuổi theo nó chỉ tạo ra test khoá cứng cách báo cáo
    # trông như thế nào — thứ sẽ cản mọi lần đổi định dạng sau này. Loại từ đầu
    # và nói rõ vì sao, thay vì để tỷ lệ bị kéo xuống bởi nhiễu.
    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Mult) and any(
                isinstance(x, ast.Constant) and isinstance(x.value, str)
                for x in (node.left, node.right)):
            return node          # không đi vào trong, không đột biến
        self.generic_visit(node)
        return node

    # hằng số:  n  thành  n + 1   ·  chuỗi thành chuỗi khác
    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            if self._hit(f"hằng {node.value} -> {not node.value}", node):
                return ast.copy_location(ast.Constant(not node.value), node)
        elif isinstance(node.value, int):
            if self._hit(f"hằng {node.value} -> {node.value + 1}", node):
                return ast.copy_location(ast.Constant(node.value + 1), node)
        return node

    # and <-> or
    def visit_BoolOp(self, node):
        self.generic_visit(node)
        new = ast.Or if isinstance(node.op, ast.And) else ast.And
        if self._hit(f"{type(node.op).__name__} -> {new.__name__}", node):
            node.op = new()
        return node

    # bỏ phủ định:  not x  thành  x
    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not):
            if self._hit("bỏ `not`", node):
                return node.operand
        return node

    # vô hiệu hoá một nhánh:  if cond:  thành  if False:
    def visit_If(self, node):
        self.generic_visit(node)
        if self._hit("vô hiệu hoá nhánh `if`", node):
            node.test = ast.copy_location(ast.Constant(False), node.test)
        return node


def count_sites(tree):
    # Đếm trên chính cây gốc, KHÔNG qua `ast.unparse` rồi parse lại — làm vậy số
    # dòng báo ra là của mã đã dựng lại, không phải của tệp thật, và báo cáo
    # "dòng 44" sẽ trỏ vào chỗ không liên quan.
    m = Mutator()
    m.visit(tree)
    return m.sites


def apply_mutation(src, index):
    tree = ast.parse(src)
    m = Mutator(target=index)
    tree = m.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# ─────────────────────────────────────────────────────────────── chạy thử

def tests_pass(spike_dir):
    env = dict(os.environ, SPIKE_DIR=spike_dir, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, RUNNER], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=180)
    return p.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--only", help="chỉ đột biến một tệp")
    args = ap.parse_args()

    targets = [args.only] if args.only else TARGETS

    print("Kiểm chứng bộ test bằng đột biến")
    print("=" * 62)

    # Điều kiện cần: mã chưa bị phá thì bộ test phải xanh. Không có bước này thì
    # mọi đột biến đều "bị bắt" vì một lý do chẳng liên quan.
    if not tests_pass(SPIKE):
        print("DỪNG — bộ test đã đỏ sẵn khi chưa đột biến gì. Sửa nó trước.")
        return 2

    total = killed = 0
    survivors = []

    work = tempfile.mkdtemp(prefix="mutants-")
    try:
        for fname in targets:
            path = os.path.join(SPIKE, fname)
            src = open(path, encoding="utf-8").read()
            sites = count_sites(ast.parse(src))
            print(f"\n{fname}: {len(sites)} vị trí")

            for i, (desc, line) in enumerate(sites):
                sandbox = os.path.join(work, f"{fname}-{i}")
                shutil.copytree(SPIKE, sandbox,
                                ignore=shutil.ignore_patterns("__pycache__",
                                                              "gallery"))
                try:
                    mutated = apply_mutation(src, i)
                except Exception:
                    continue          # đột biến tạo mã không hợp lệ — bỏ qua
                open(os.path.join(sandbox, fname), "w",
                     encoding="utf-8").write(mutated)

                total += 1
                try:
                    survived = tests_pass(sandbox)
                except subprocess.TimeoutExpired:
                    survived = False  # đột biến gây treo cũng tính là bị bắt
                shutil.rmtree(sandbox, ignore_errors=True)

                if survived:
                    survivors.append((fname, line, desc))
                    if args.verbose:
                        print(f"  SỐNG  dòng {line}: {desc}")
                else:
                    killed += 1
                    if args.verbose:
                        print(f"  chết  dòng {line}: {desc}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("\n" + "=" * 62)
    rate = (killed / total * 100) if total else 0
    print(f"{killed}/{total} đột biến bị bắt  ({rate:.0f}%)")

    if survivors:
        print(f"\n{len(survivors)} đột biến SỐNG SÓT — mỗi dòng là một hành vi "
              f"không test nào canh:")
        for fname, line, desc in survivors:
            print(f"  {fname}:{line}  {desc}")
        print("\nViết test giết chúng, hoặc ghi vào CLAUDE.md vì sao chấp nhận được.")

    # Không đòi 100%. Một số đột biến tương đương về ngữ nghĩa (đổi hằng trong
    # chuỗi hiển thị, vô hiệu hoá nhánh chỉ ảnh hưởng định dạng) và đuổi theo
    # chúng là lãng phí. Nhưng ngưỡng phải tồn tại, nếu không con số chỉ để ngắm.
    THRESHOLD = 80
    if rate < THRESHOLD:
        print(f"\nKHÔNG ĐẠT — dưới ngưỡng {THRESHOLD}%.")
        return 1
    print(f"ĐẠT — từ ngưỡng {THRESHOLD}% trở lên.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
