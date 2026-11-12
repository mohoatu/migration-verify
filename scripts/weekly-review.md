# Soát Chủ nhật — 20 phút, không hơn

Vòng chất lượng có ba nhịp: **snapshot mỗi giờ** (tự động) → **soát Chủ nhật**
(tệp này) → **bộ test tự kiểm chứng** (`tests/mutate.py`).

Đây là nhịp giữa. Nó tồn tại vì để agent sửa mã cả tuần thì repo trôi theo cách
không ai để ý trong từng commit riêng lẻ, chỉ thấy khi nhìn cả tuần.

---

## Chạy trước, đọc sau

```bash
python3 tests/run.py          # phải xanh
python3 tests/mutate.py       # phải ≥ 80%, và nên là 100%
git log --oneline -20
git diff --stat HEAD~20       # tuần này đã động vào những gì
wc -l spike/*.py
```

---

## Sáu câu hỏi

**1. Tỷ lệ đường ống / phân loại có trôi không?**

`classify.py` đang bao nhiêu dòng? Mốc là **48**. Phình lên nghĩa là luật riêng
của khách đang chui vào mã — và đó là ranh giới giữa sản phẩm và tư vấn. Nếu nó
phình, xem phần thêm vào có thể đẩy sang `schema.json` được không.

**2. Có chữ nào thuộc nghiệp vụ lọt vào `classify.py` chưa?**

`tests/run.py` đã canh một danh sách từ khoá, nhưng danh sách đó không đầy đủ.
Đọc bằng mắt một lượt. Thấy "lãi", "claim", "policy" thì sửa ngay, và thêm từ đó
vào test.

**3. Đột biến nào sống sót tuần này?**

Mỗi đột biến sống sót là một hành vi không ai canh. Hoặc viết test giết nó, hoặc
ghi vào `CLAUDE.md` vì sao chấp nhận được. **Không để tồn đọng sang tuần sau** —
để hai tuần là bắt đầu quen với việc có lỗ thủng.

**4. Số liệu trong tài liệu còn khớp không?**

`KET-QUA.md`, `linkedin-post.md`, ảnh trong `spike/gallery/` và listing Upwork
đều chứa con số. Chạy lại hai kịch bản, so với những gì đã viết. Lệch thì sửa
tài liệu, đừng sửa kỳ vọng.

```bash
cd spike && python3 generate.py && python3 verify.py legacy_output.txt modern_output.txt schema.json | head -3
```

**5. Có dữ liệu khách nào lọt vào repo không?**

```bash
git log --all --name-only --format= | sort -u | grep -iE 'customer|cust|prod' || echo "sạch"
```

Lọt rồi thì `git rm` không đủ — nó vẫn nằm trong lịch sử. Xử lý ngay trong tuần
đó, đừng để lâu.

**6. Tuần này có thêm tính năng nào chưa ai hỏi không?**

Kế hoạch ghi: không viết mã sản phẩm cho tới khi có tín hiệu từ ngoài. Nếu tuần
qua có tính năng mới mọc ra, hỏi lại: **có ai yêu cầu không?** Không thì cân nhắc
gỡ. Mã chưa ai cần vẫn phải nuôi.

---

## Dọn

- Xoá nhánh đã merge, xoá tệp tạm, xoá `__pycache__`
- Snapshot cũ hơn 2 tuần: `git update-ref -d refs/heads/snapshots` rồi chụp lại
- Ghi chú một dòng vào cuối tệp này: tuần này sửa gì, còn treo gì

---

## Nhật ký

<!-- Thêm một dòng mỗi tuần. Ngắn thôi. -->

- **2026-11-12** — Dựng harness: 115 kiểm tra, 48/48 đột biến bị bắt, bộ dựng
  lược đồ + sub-agent đọc tệp lớn. Chưa có khách. Còn treo: đăng listing Upwork,
  bài follow-up LinkedIn.
