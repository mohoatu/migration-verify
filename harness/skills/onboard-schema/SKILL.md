---
name: onboard-schema
description: Biến tệp kết quả batch của một khách hàng mới thành `schema.json` dùng được, rồi chạy thử đối chiếu lần đầu. Dùng khi khách gửi tệp dữ liệu, khi bắt đầu một đơn Project Catalog, hoặc khi cần khai một định dạng tệp chưa gặp.
---

# Nhận tệp của khách → lược đồ dùng được

Đây là **việc lặp lại duy nhất** của nghề này. Mọi đơn hàng đều bắt đầu bằng nó,
và nó là chỗ tốn thời gian nhất nếu làm tay.

Mục tiêu không phải ra lược đồ nhanh. Mục tiêu là ra lược đồ **đúng** — vì một
lược đồ sai kiểu hay sai khoá sẽ làm mọi phân loại phía sau sai theo, và báo cáo
vẫn trông rất thuyết phục.

---

## Trước khi chạm vào tệp

Chép tệp của khách vào `customer/<tên-khách>/`. Thư mục đó đã nằm trong
`.gitignore`. **Không bao giờ để dữ liệu khách ở chỗ khác trong repo**, kể cả tạm.

Nếu khách gửi dữ liệu thật chưa che: hỏi xem có bản che được không. Không có thì
vẫn làm, nhưng không trích giá trị cụ thể vào bất kỳ ghi chú, báo cáo hay tin
nhắn nào.

---

## Bước 1 — Để máy đếm trước

```bash
python3 scripts/profile_file.py customer/<khách>/legacy.txt \
                                customer/<khách>/legacy_run2.txt \
                                --out customer/<khách>/schema.json
```

Tham số thứ hai là **lần chạy thứ hai của chính hệ CŨ**, không phải bản sau
migration. Đó là cách duy nhất biết trường nào đổi theo lần chạy. Chưa xin được
thì bỏ trống — công cụ sẽ nói rõ phần đó chỉ là phỏng đoán.

Thêm `--name` nếu có Ollama hay LM Studio đang chạy: mô hình cục bộ đặt tên cột,
và **chỉ đặt tên**. Không có thì tên là `field_00`, đổi tay sau.

## Bước 2 — Đọc cảnh báo trước khi đọc lược đồ

Công cụ in cảnh báo ra `stderr`. Ba loại, không được bỏ qua loại nào:

| Cảnh báo | Nghĩa là | Phải làm gì |
|---|---|---|
| không tìm được khoá | sẽ phải ghép theo số dòng | **hỏi khách** tổ hợp nào định danh một bản ghi; không có khoá thì báo giá lại |
| trường ngày mơ hồ | `03/06/2026` khớp cả dd/mm lẫn mm/dd | **hỏi khách**, rồi để lại đúng một định dạng trong `formats` |
| hai trường bị gộp | tệp cố định không có khoảng trắng ngăn | **xin copybook** hoặc bản mô tả định dạng |

Cả ba đều là câu hỏi cho khách, không phải việc để đoán. Đoán sai định dạng ngày
là **âm thầm bỏ qua một lỗi thật** — nguy hơn báo nhầm, vì báo nhầm thì người ta
thấy.

## Bước 3 — Dọn lược đồ bằng tay

Xoá các khoá chẩn đoán: `_sample`, `_distinct`, `_profiled`, `_AMBIGUOUS`,
`_MERGED`. Rồi soát ba thứ, theo thứ tự quan trọng:

1. **Trường nào là số nguyên?** Số nguyên không có dung sai, nên khai nhầm một
   cột số nguyên thành thập phân là tự tay mở cho lỗi lọt qua. Số ngày, cờ, mã
   hạng, số lần lặp — tất cả phải là `integer`.
2. **Scale của từng trường thập phân** có khớp với mức khách thật sự quan tâm
   không. Khai scale rộng hơn thực tế là nới dung sai mà không ai biết.
3. **Danh sách `volatile`** có đúng là thứ đổi mỗi lần chạy không. Khai nhầm một
   cột là volatile nghĩa là **vĩnh viễn không bao giờ kiểm tra cột đó nữa**. Khi
   phân vân, bỏ ra khỏi danh sách — thừa một cảnh báo còn hơn thiếu một lỗi.

## Bước 4 — Chạy thử lần đầu

```bash
python3 spike/verify.py customer/<khách>/legacy.txt \
                        customer/<khách>/modern.txt \
                        customer/<khách>/schema.json --lang=en
echo $?
```

Đọc kết quả theo thứ tự này:

- **Hàng nghìn SAI NGHIỆP VỤ** → gần như chắc chắn lược đồ sai, không phải
  migration sai. Hay gặp nhất: lệch cột, hoặc ngày đổi định dạng mà chưa khai
  kiểu `date`. Quay lại bước 3.
- **Số bản ghi so sánh ít hơn số dòng tệp** → khoá không duy nhất, bản ghi bị
  gộp. Quay lại bước 1.
- **Vài chục SAI NGHIỆP VỤ tập trung ở một hai trường** → đây mới là kết quả
  thật. Đem cho khách.

## Bước 5 — Giao

Báo cáo trả lời một câu ở dòng đầu, và danh sách bản ghi cần người xem ở dưới.
Kèm theo:

- `schema.json` đã dọn — khách giữ, chạy lại được bất cứ lúc nào
- Danh sách câu hỏi còn treo từ bước 2
- Một câu nói rõ **những gì công cụ không kiểm được**: nó so sánh kết quả, không
  đọc mã nguồn; chỗ nào hai hệ cùng sai giống nhau thì nó không thấy

Điểm cuối không phải khiêm tốn cho đẹp. Nó là ranh giới của dịch vụ, và nói
trước thì không bị trách sau.

---

## Việc KHÔNG làm trong quy trình này

- **Không sửa `classify.py` cho vừa tệp của khách.** Nếu phải sửa, dừng lại và
  hỏi — đó là tín hiệu công cụ đang biến thành tư vấn, và `CLAUDE.md` giải thích
  vì sao điều đó quan trọng.
- **Không nới dung sai để báo cáo ngắn lại.** Báo cáo dài là triệu chứng, không
  phải bệnh.
- **Không commit bất cứ thứ gì trong `customer/`.**
