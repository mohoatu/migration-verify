# Đặc tả nghiệp vụ — PREMCALC

> Tài liệu này mô phỏng thứ mà một đội migration thật nhận được: mô tả **cần tính
> cái gì**, không mô tả **chương trình cũ tính thế nào**. Nó được viết trước khi
> viết bản Java, và bản Java chỉ được phép đọc tệp này.
>
> Những chỗ tài liệu im lặng là **cố ý**. Ngoài đời đặc tả luôn im lặng ở đâu đó,
> và chính những chỗ im lặng đó là nơi bản dịch lệch đi.

---

## Mục đích

Job chạy hằng ngày. Đọc tệp danh sách hợp đồng, tính lãi dồn và số tiền mỗi kỳ
trả góp, xuất báo cáo cho bộ phận nghiệp vụ.

## Tệp vào — `policies.dat`

Bề rộng cố định, mỗi dòng một hợp đồng, không có dòng tiêu đề.

| Vị trí | Dài | Trường | Kiểu |
|---|---|---|---|
| 0 | 10 | mã hợp đồng | chuỗi |
| 10 | 8 | ngày bắt đầu, `YYYYMMDD` | chuỗi |
| 18 | 9 | tiền gốc, 2 số lẻ, **không có dấu chấm** (`000123456` = 1.234,56) | số |
| 27 | 5 | lãi suất, đơn vị điểm cơ bản (`00750` = 7,50 %/năm) | số nguyên |
| 32 | 4 | số ngày của kỳ hạn | số nguyên |
| 36 | 2 | số kỳ trả góp | số nguyên |
| 38 | 1 | hạng khách (`1`, `2`, `3`) | chuỗi |

## Tệp ra — `*_out.txt`

Bề rộng cố định, mỗi hợp đồng một dòng, theo đúng thứ tự tệp vào, cuối tệp có
một dòng tổng kiểm soát.

| Vị trí | Dài | Trường | Định dạng |
|---|---|---|---|
| 0 | 10 | mã hợp đồng | chuỗi |
| 10 | 4 | số ngày tính lãi | số, đệm số 0 bên trái |
| 14 | 10 | tiền mỗi kỳ | `9999999.99` |
| 24 | 10 | tiền lãi | `9999999.99` |
| 34 | 10 | tổng phải trả | `9999999.99` |
| 44 | 2 | mã trạng thái | chuỗi |
| 46 | 14 | khoảng trắng | |

Dòng tổng kiểm soát: `TRAILER   ` + số bản ghi (6 chữ số, đệm 0) + tổng của
*tổng phải trả* theo định dạng `999999999.99` + khoảng trắng cho đủ bề rộng.

## Quy tắc tính

**1. Số ngày tính lãi.** Bằng số ngày của kỳ hạn, nhưng **không quá 365**.

**2. Lãi suất ngày.** Lãi suất năm chia cho 365. Lãi suất năm lấy từ điểm cơ bản
chia 10000.

**3. Tiền lãi.** `tiền gốc × lãi suất ngày × số ngày tính lãi`.

**4. Tổng phải trả.** `tiền gốc + tiền lãi`.

**5. Tiền mỗi kỳ.** `tổng phải trả ÷ số kỳ`.

**6. Bù phần dư.** Tổng các kỳ phải bằng đúng tổng phải trả. Phần chênh lệch
cộng vào kỳ cuối.

**7. Mã trạng thái.** Một hợp đồng có đúng một mã:

- `PD` — hạng 3 **và** tiền gốc trên 40.000,00
- `MX` — số ngày tính lãi chạm trần 365
- `LS` — trả một lần duy nhất (số kỳ bằng 1)
- `AP` — các trường hợp còn lại

**8. Tổng kiểm soát.** Cộng dồn *tổng phải trả* của mọi bản ghi.

---

## Những gì đặc tả này KHÔNG nói

Liệt kê ở đây để sau khi so sánh xong còn đối chiếu lại, chứ người viết bản Java
không cần nhìn danh sách này — họ chỉ cần không tìm thấy câu trả lời ở trên.

1. **Mỗi bước tính giữ mấy chữ số thập phân, và cắt hay làm tròn?**
2. **Quy tắc 7: một hợp đồng thoả nhiều điều kiện thì lấy mã nào?** Đặc tả nói
   "đúng một mã" nhưng không nói thứ tự ưu tiên.
3. **"Trên 40.000,00" là `>` hay `>=`?**
4. **Trần 365 áp trước hay sau khi tính lãi?**
5. **Tổng kiểm soát tràn số thì sao?**
6. **Quy tắc 6: "kỳ cuối" khi chỉ có một kỳ thì xử lý thế nào?**

Sáu chỗ này là nơi hai bản cài đặt sẽ lệch nhau. Nếu công cụ đối chiếu chỉ ra
đúng chúng, nó làm được việc nó hứa.
