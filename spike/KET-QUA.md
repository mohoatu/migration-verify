# Kết quả spike — sản phẩm hay tư vấn?

Chạy **10/11/2026**. Spike này được dựng để trả lời **một** câu, và nó đã trả lời.

---

## Câu hỏi

> Khi so sánh kết quả trước và sau migration, bao nhiêu phần công việc là **đường
> ống** (đọc tệp, ghép bản ghi, in báo cáo), và bao nhiêu phần là **phân loại**
> khác biệt?
>
> Nếu phân loại chiếm phần lớn và mỗi khách lại cần luật riêng → đây là **tư vấn**.
> Nếu phân loại gọn và dùng lại được → đây là **sản phẩm**.

---

## Bài toán dựng ra

Job tính lãi dồn hằng ngày, **2.000 tài khoản**, báo cáo rộng cố định — dạng job phổ
biến nhất còn sống trong hệ thống cũ.

Bốn khác biệt gieo vào bản "sau migration", lấy từ lỗi có thật:

| # | Khác biệt | Quy mô | Bản chất |
|---|---|---|---|
| 1 | COBOL **cắt** số, Java **làm tròn** | 2.026 trường | vô hại, nhưng phải ký duyệt |
| 2 | Bản mới ghi theo thứ tự sắp xếp | cả 2.000 dòng | vô hại |
| 3 | Dấu thời gian ở dòng tiêu đề | 1 dòng | vô hại |
| 4 | **`UNTIL` dịch nhầm thành `while`** → thừa một ngày lãi | **4 tài khoản** | **tiền sai, chặn go-live** |

Lỗi thứ tư chỉ chạm các tài khoản đáo hạn **đúng vào biên**. Đó là hình dạng thật của
một lỗi migration: không sai hàng loạt, mà sai một nhóm nhỏ, lặng lẽ.

---

## Kết quả

### `diff` thông thường

```
diff legacy modern              → 3.874 dòng khác biệt
sort rồi mới diff (công bằng)   → 2.036 dòng khác biệt
```

**Bốn tài khoản sai thật bị chôn trong hơn hai nghìn dòng nhiễu.** Đây chính xác là
lý do người ta chạy song song hai năm: không ai đọc hết nổi, và không ai dám nói chỗ
nào bỏ qua được.

### Công cụ của spike

```
KHÔNG ĐẠT — 12 khác biệt phải xử lý, trên 4 bản ghi

  SAI NGHIỆP VỤ                12  ← chặn
  Làm tròn / biểu diễn       2026

  trường `accrual_days`: 4 bản ghi
  trường `interest`:     4 bản ghi
  trường `total`:        4 bản ghi

  ACC0000901  accrual_days: 365 → 366
  ACC0000901  interest: 712.26 → 714.22   (lệch 1.96, vượt quá một đơn vị)
```

**Tìm đúng cả 4 tài khoản. Không sót, không báo nhầm.** Mã thoát `1` — dùng được làm
cổng chặn trong CI.

Từ **2.036 dòng phải đọc** xuống **4 tài khoản phải quyết định**.

---

## Trả lời câu hỏi: **sản phẩm**

Số dòng mã, bỏ dòng trống và chú thích:

| Tệp | Vai trò | Dòng |
|---|---|---|
| `records.py` | đọc, ghép theo khoá | 57 |
| `report.py` | in báo cáo | 55 |
| `verify.py` | ghép lại, mã thoát | 29 |
| **`classify.py`** | **phân loại khác biệt** | **44** |

**Đường ống 141 dòng, phân loại 44 dòng — tỷ lệ 76 / 24.**

Và quan trọng hơn con số: **44 dòng phân loại đó không có gì riêng của khách hàng
nào.** Luật là:

- trường được khai là đổi theo lần chạy → bỏ qua
- số thập phân lệch trong phạm vi một đơn vị nhỏ nhất → làm tròn
- số thập phân lệch hơn thế → sai nghiệp vụ
- **số nguyên lệch bất kỳ → sai nghiệp vụ, không có dung sai**
- chuỗi lệch → sai nghiệp vụ

Không luật nào nhắc tới lãi suất, tài khoản, hay ngân hàng. Chúng là luật về **kiểu
dữ liệu**, không phải về nghiệp vụ. Phần duy nhất khách phải khai là **lược đồ tệp**
— và lược đồ thì họ vốn đã có, vì hệ thống cũ phải có nó mới ghi được tệp.

---

## Phát hiện quan trọng nhất, và nó không nằm trong dự tính

Dung sai làm tròn **đáng lẽ phải che mất** lỗi thật: hai trong bốn tài khoản sai chỉ
lệch `0,08` và `0,02` ở cột tiền — thừa một ngày lãi trên số dư nhỏ. Nếu chỉ nhìn
cột tiền thì chúng lẫn vào 2.026 bản ghi làm tròn.

Chúng bị bắt vì trường `accrual_days` — **một số nguyên lệch đúng 1**.

> **Đừng tìm tiền sai. Hãy tìm nguyên nhân sai.**
>
> Tiền là kết quả, và kết quả có dung sai tự nhiên để nấp sau. Số ngày, cờ trạng
> thái, số lần lặp, mã phân loại — đó là nguyên nhân, và chúng **không có dung sai
> nào cả**. Một số nguyên lệch 1 thì luôn là có chuyện.

Đây là luận điểm của cả sản phẩm, và em không nghĩ ra nó trước khi chạy — nó rơi ra
từ dữ liệu. Nó cũng là thứ đáng viết thành bài kỹ thuật.

---

## Giới hạn — chưa chứng minh được gì ngoài những điều sau

Spike làm trên **dữ liệu do chính nó sinh ra**. Nghĩa là:

- **Lược đồ sạch và biết trước.** Tệp thật có bản ghi nhiều loại trong cùng một tệp,
  trường gói (`COMP-3`), EBCDIC, độ dài thay đổi. Phần đọc tệp sẽ phình to.
- **Khoá tồn tại và duy nhất.** Nhiều báo cáo thật không có khoá tự nhiên.
- **Chưa thử trên tệp lớn.** 2.000 bản ghi chạy tức thì; hàng chục triệu thì khác.
- **Chưa ai ngoài em nhìn kết quả này.** Nó chứng minh *làm được*, chưa chứng minh
  *có người trả tiền*.

Nhưng câu hỏi sống còn đã có đáp án: **phần có giá trị thì nhỏ, gọn, và dùng chung
được giữa các khách hàng.** Đây là hình dạng sản phẩm, không phải hình dạng tư vấn.

---

## Kịch bản 2 — kiểm tra lại kết luận trên

Kết luận "sản phẩm" ở trên chỉ dựa trên **một** bài toán, nên nó chưa đáng tin.
Kịch bản 2 được dựng để phá nó: nếu luật phân loại phải viết lại cho bài toán
mới thì đây là tư vấn, không phải sản phẩm.

Cố tình khác hình dạng ở bốn điểm:

| | Kịch bản 1 | Kịch bản 2 |
|---|---|---|
| Định dạng tệp | bề rộng cố định | phân tách bằng `\|` |
| Khoá ghép | một trường | **hai** trường |
| Lỗi nghiệp vụ nằm ở | số tiền | **mã trạng thái (chuỗi)** |
| Bản ghi mất | không | **có** |

Bài toán: job xét duyệt yêu cầu bảo hiểm, 1.500 dòng. Hai lỗi thật gieo vào:

- **15 dòng** mã `adjudication` ghi `DN` (từ chối) thay vì `PD` (từ chối một phần).
  **Tiền vẫn đúng tới từng xu — chỉ *lý do* là sai.** Đây là loại lỗi tệ nhất
  ngoài đời, và không công cụ nào chỉ đối chiếu cột tiền bắt được nó.
- **10 dòng mất hẳn** vì điều kiện lọc `>` dịch nhầm thành `>=`.

Nhiễu gieo vào: đổi định dạng ngày (`2026-06-03` → `03/06/2026`, cả 1.500 dòng),
chuẩn hoá tên nhà cung cấp (cắt khoảng trắng + đổi HOA, cả 1.500 dòng), lệch làm
tròn, và dấu thời gian ở tiêu đề.

### Lần chạy thứ nhất — thất bại, và đó là chỗ học được

```
KHÔNG ĐẠT — 4500 khác biệt phải xử lý, trên 1500 bản ghi
  trường `service_date`: 1500 bản ghi      ← báo nhầm
  trường `provider`:     1500 bản ghi      ← báo nhầm
  trường `adjudication`:   15 bản ghi      ← đúng
```

**3.000 báo nhầm.** Luật của kịch bản 1 xếp mọi chuỗi lệch vào SAI NGHIỆP VỤ, nên
đổi định dạng ngày và đổi hoa/thường đều bị coi là tiền sai. Một công cụ như vậy
vô dụng y như `diff`.

Câu hỏi quyết định không phải "có phải sửa không" mà **"phải sửa bằng luật chung
hay bằng luật riêng của khách này"**. Hai chỗ sửa, cả hai đều chung:

1. **Ngày**: đọc `2026-06-03` và `03/06/2026` thành cùng một `date` — việc của
   **đường ống**, không phải của phân loại. Hai cách viết của cùng một ngày thì
   không phải hai giá trị lệch.
2. **Chuỗi**: thêm một loại `FORMATTING` — bằng nhau sau khi cắt khoảng trắng và
   bỏ phân biệt hoa/thường thì là khác **cách viết**. Vẫn báo (một mã phân loại
   đổi hoa/thường có thể làm hệ phía sau khớp sai) nhưng **không chặn**.

Không luật nào nhắc tới bảo hiểm, nhà cung cấp, hay mã xét duyệt.

### Lần chạy thứ hai

```
KHÔNG ĐẠT — 25 khác biệt phải xử lý, trên 25 bản ghi

  SAI NGHIỆP VỤ                15  ← chặn
  MẤT BẢN GHI                  10  ← chặn
  Làm tròn / biểu diễn        727
  Khác cách viết             1490

  CLM000085/1  adjudication: PD → DN
  CLM000147/3  adjudication: PD → DN
```

**15 + 10 = đúng 25, khớp chính xác số lỗi gieo vào. Không sót, không báo nhầm.**
Kịch bản 1 chạy lại vẫn ra đúng 4 bản ghi như cũ — luật mới không phá luật cũ.

`diff` trên cùng cặp tệp: **2.992 dòng**, và sort trước cũng vẫn 2.992.

### Giá phải trả, đo bằng dòng mã

| | Kịch bản 1 | Sau kịch bản 2 | Thêm |
|---|---|---|---|
| Đường ống | 141 | 158 | **+17** |
| Phân loại | 44 | 48 | **+4** |

Để đỡ thêm một định dạng tệp khác, khoá ghép hai trường, ngày đổi định dạng, chuỗi
đổi hoa/thường, và một **lớp lỗi hoàn toàn mới** (sai mã chứ không sai tiền): tốn
**21 dòng, trong đó 4 dòng ở phần phân loại.** Số luật riêng cho khách hàng: **0**.

Đây là bằng chứng mạnh hơn kịch bản 1 nhiều, vì nó là kết quả của một lần **cố ý
phá**.

---

## Rủi ro mới mà kịch bản 2 lộ ra

Phần đọc ngày thử lần lượt `%Y-%m-%d`, `%d/%m/%Y`, `%Y%m%d`, `%m/%d/%Y`… Với
`03/06/2026` thì `%d/%m/%Y` khớp trước nên ra **3 tháng 6**. Nhưng nếu hệ mới thật
sự ghi theo kiểu Mỹ thì đó là **6 tháng 3**, và công cụ sẽ **im lặng bỏ qua một
lỗi thật**.

Đây nguy hiểm hơn một báo nhầm: báo nhầm thì người ta thấy, còn đoán sai định dạng
thì không ai thấy. Nên `formats` phải khai được **theo từng trường** trong lược đồ
(đã làm), và phiên bản thật phải **từ chối chạy** khi một trường ngày khớp được
nhiều hơn một định dạng có nghĩa — thà bắt khách khai rõ còn hơn đoán.

---

## Chạy lại

```bash
cd spike

# kịch bản 1 — job tính lãi, lỗi ở số tiền
python3 generate.py
python3 verify.py legacy_output.txt modern_output.txt schema.json

# kịch bản 2 — job xét duyệt bảo hiểm, lỗi ở mã trạng thái + mất bản ghi
python3 generate2.py
python3 verify.py legacy2.txt modern2.txt schema2.json

echo $?    # 1 = có chỗ chặn
```

Không cần cài gì. Python chuẩn, không thư viện ngoài.
