# migration-verify

Chứng minh một cuộc migration **không làm sai nghiệp vụ** — bằng cách so sánh kết
quả của job xử lý theo lô trước và sau, rồi phân loại từng khác biệt.

> Trạng thái: **spike, chưa có khách hàng, chưa có doanh thu.** Mọi số liệu dưới
> đây đo trên dữ liệu tự sinh. Giới hạn ghi ở [`spike/KET-QUA.md`](spike/KET-QUA.md).

---

## Vấn đề

Bạn viết lại một job batch — COBOL sang Java, monolith thành dịch vụ, Oracle sang
PostgreSQL. Mã mới chạy được. Câu không ai trả lời được là **nó có còn ra đúng
những con số đó không**.

Nên bạn chạy song song hai hệ rồi `diff`. Và `diff` trả về hai nghìn dòng, vì hệ
mới làm tròn chỗ hệ cũ cắt số, ghi bản ghi theo thứ tự khác, đóng dấu thời gian
khác. Đâu đó trong hai nghìn dòng ấy có ba bản ghi tiền thật sự sai. Không ai tìm
ra, và không ai muốn là người ký rằng "mấy chỗ lệch kia không sao".

## Công cụ này

```
                     diff      công cụ này
kịch bản 1     3.874 dòng   →   4 tài khoản, có tên
kịch bản 2     2.992 dòng   →   25 bản ghi, có tên
```

Không sót, không báo nhầm, trên cả hai kịch bản. Mã thoát khác 0 khi có chỗ chặn,
nên nó dùng được làm cổng trong CI.

Mỗi khác biệt rơi vào một trong năm loại:

| | | |
|---|---|---|
| `RUN-VARIABLE` | dấu thời gian, số thứ tự lô | bỏ qua |
| `FORMATTING` | cùng giá trị, khác cách viết | báo, không chặn |
| `ROUNDING` | trong phạm vi một đơn vị nhỏ nhất | cần ký duyệt |
| `BUSINESS` | logic đổi — tiền hoặc ý nghĩa đã dịch chuyển | **chặn** |
| `MISSING` / `EXTRA` | bản ghi mất hoặc mọc thêm | **chặn** |

Bản ghi được ghép **theo khoá nghiệp vụ**, không theo số dòng — nên đảo thứ tự
không biến thành hàng nghìn khác biệt giả.

## Luận điểm

> **Đừng tìm tiền sai. Hãy tìm nguyên nhân sai.**

Trong kịch bản 1, hai trong bốn lỗi thật chỉ lệch `0,08` và `0,02` ở cột tiền —
nằm gọn trong dung sai làm tròn cần thiết để dập 2.026 khác biệt vô hại. Nhìn vào
tiền thì chúng vô hình.

Chúng bị bắt vì `accrual_days`: một **số nguyên lệch đúng 1**.

Tiền là kết quả, và kết quả có dung sai tự nhiên để nấp sau. Số ngày, cờ trạng
thái, số lần lặp, mã hạng — đó là nguyên nhân, và chúng không có dung sai nào cả.
Vì vậy ở đây **trường số nguyên không có dung sai, vĩnh viễn**.

---

## Chạy thử

Không cần cài gì. Python 3 chuẩn, không thư viện ngoài.

```bash
cd spike
python3 generate.py  && python3 verify.py legacy_output.txt modern_output.txt schema.json  --lang=en
python3 generate2.py && python3 verify.py legacy2.txt       modern2.txt       schema2.json --lang=en
echo $?        # 1 = có chỗ chặn
```

## Phát triển

```bash
python3 tests/run.py        # 115 kiểm tra
python3 tests/mutate.py     # 48/48 đột biến bị bắt — bộ test tự chứng minh nó biết fail
```

Cái thứ hai quan trọng hơn cái thứ nhất. Sản phẩm này **chính là** một bộ kiểm
thử: khách trả tiền để nghe câu "không có gì sai". Một công cụ không chứng minh
được nó biết nói "có cái sai" thì câu trả lời của nó vô nghĩa.

Đọc [`CLAUDE.md`](CLAUDE.md) trước khi sửa bất cứ thứ gì.
