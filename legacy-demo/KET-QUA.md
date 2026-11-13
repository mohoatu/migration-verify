# Kịch bản 3 — Perl thật so với Java thật

Chạy **13/11/2026**. Đây là kịch bản đầu tiên **không ai gieo khác biệt vào**.

---

## Khác gì hai kịch bản trước

`spike/KET-QUA.md` ghi rõ giới hạn lớn nhất của hai kịch bản kia: một script
sinh ra **cả hai** tệp kết quả rồi tự cấy lỗi vào bản "sau migration". Biết
trước câu trả lời thì bài kiểm tra dễ hơn thực tế rất nhiều.

Lần này:

| | Kịch bản 1 & 2 | Kịch bản 3 |
|---|---|---|
| Tệp kết quả | một script sinh cả hai | **hai chương trình độc lập tự tính** |
| Khác biệt | gieo vào có chủ đích | **không ai biết trước** |
| Ngôn ngữ cũ | không có | **Perl 5.34** |
| Ngôn ngữ mới | không có | **Java 21** |

Quy trình: viết [`SPEC.md`](SPEC.md) **trước** — đặc tả nghiệp vụ trung lập về
ngôn ngữ, mô tả *cần tính gì* chứ không mô tả *chương trình cũ tính thế nào*.
Viết `legacy/premcalc.pl` theo kiểu một script batch 2004 còn sót lại. Rồi viết
`modern/PremCalc.java` **chỉ từ đặc tả**, không mở lại tệp Perl.

### Vì sao Perl chứ không phải COBOL

Khoảng trống thị trường đã xác định là *"hệ 15 năm tuổi, không có mainframe"*.
COBOL thì IBM đã có watsonx Code Assistant for Z và một bài ASE '24 về đúng việc
kiểm chứng bản dịch — lấy COBOL làm ví dụ là tự đứng cạnh IBM.

Perl là ngôn ngữ batch "không ai muốn động vào" lớn nhất **ngoài** mainframe:
ETL và sinh báo cáo ở ngân hàng, viễn thông, bảo hiểm giai đoạn 1998–2010, giờ
đang được viết lại sang Java. Không có IBM, Google hay Atos ở đó.

Về kỹ thuật cũng hợp hơn: Perl dùng số thực IEEE và `sprintf` làm tròn
half-to-even; Java `BigDecimal` thì chính xác tuyệt đối. Hai cái đó **chắc chắn
lệch nhau ở hàng xu**, theo kiểu không đoán trước được.

*(`PREMCALC.cbl` trong `cobol-demo/` giữ lại làm tài liệu. GnuCOBOL không chạy
được trên máy này: Smart App Control chặn mọi binary không ký.)*

---

## Kết quả

1.200 hợp đồng. `diff` thô: **2.402 dòng**. 578 bản ghi giống hệt nhau.

```
DO NOT SHIP — 354 khác biệt phải xử lý, trên 354 bản ghi

  SAI NGHIỆP VỤ               354  <- chặn
  Làm tròn / biểu diễn        275

  trường `instalment`: 354 bản ghi

Cần ký duyệt
  trường `instalment`: 266 · `total_due`: 5 · `interest`: 3 · `sum_due`: 1
```

### 354 chỗ sai nghiệp vụ đều do **một câu thiếu trong đặc tả**

Quy tắc 5 nói *"tiền mỗi kỳ = tổng ÷ số kỳ"*. Quy tắc 6 nói *"phần dư cộng vào
kỳ cuối"*. Báo cáo chỉ có **một** cột tiền kỳ — và đặc tả không nói in cái nào.

- Perl in **kỳ cuối** (kỳ lẻ, kỳ mà bộ phận hỗ trợ hay bị hỏi)
- Java in **kỳ chuẩn** theo quy tắc 5

**Cả hai đều đọc đúng tài liệu.** Không ai viết sai; tài liệu thiếu một câu.
Đó là hình dạng thật của lỗi migration, và nó không lộ ra ở 578 bản ghi trùng
khớp.

### Tổng kiểm soát lệch một xu

```
Perl : TRAILER   001200 59629808.34
Java : TRAILER   001200 59629808.35
```

Sai số tích luỹ của số thực sau 1.200 bản ghi. Một xu — và là con số kiểm toán
đối chiếu đầu tiên.

---

## Hai lỗ hổng của công cụ mà kịch bản này lộ ra

Phần đáng giá nhất của ngày hôm nay không phải kết quả, mà là hai chỗ hỏng chỉ
xuất hiện khi có chương trình thật ghi tệp thật.

**1. Dòng `TRAILER` suýt bị tính là bản ghi.** Chữ `"RUNSTAMP"` bị viết cứng
trong `records.py` làm dấu hiệu dòng không-phải-bản-ghi. Tệp này kết thúc bằng
`TRAILER`, mà job batch nào cũng có dòng tổng kiểm soát. Không sửa thì nó thành
một "bản ghi mất" giả ở **mọi** lần chạy — và tệ hơn, che mất một bản ghi mất
thật. Đã chuyển vào lược đồ: `non_record_prefixes`.

**2. Công cụ chỉ nói "dòng tiêu đề có đổi", không nói đổi cái gì.** Với dòng
trailer thì đó là thiếu sót nặng: tổng kiểm soát lệch bị đẩy xuống một ghi chú
chung chung mà người đọc sẽ bỏ qua. Đã sửa: khai `trailer_fields` thì dòng
trailer được đối chiếu **theo từng trường** như bản ghi thường, và số bản ghi —
là số nguyên — không có dung sai.

Chỗ sửa thứ hai phải cẩn thận một điểm: **không được chặn khi lược đồ chưa khai
`trailer_fields`**, vì dòng tiêu đề thường chứa dấu thời gian và đổi mỗi lần
chạy. Báo cáo nay nói rõ `changed (not checked — declare trailer_fields)` thay
vì gộp chung với trường hợp đã kiểm.

Không kịch bản tự sinh nào lộ ra được hai chỗ này, vì người viết kịch bản không
nghĩ tới việc gieo một dòng trailer vào.

---

## Giới hạn

- **Cùng một người viết cả hai bản.** Có giảm nhẹ bằng cách viết đặc tả trước
  rồi viết Java chỉ từ đặc tả, nhưng vẫn yếu hơn hai người thật.
- **Không có COBOL thật**, nên chưa kiểm được `COMP-3` nhị phân, EBCDIC, hay
  nhiều loại bản ghi trong một tệp.
- **Dữ liệu đầu vào vẫn do script sinh.** Nhưng chỉ là *đầu vào* — kết quả thì
  hai chương trình tự tính, và đó là điều khác biệt so với kịch bản 1 và 2.

---

## Chạy lại

```bash
cd legacy-demo
python3 gen_policies.py
perl legacy/premcalc.pl policies.dat legacy_out.txt
javac -d build modern/PremCalc.java && java -cp build PremCalc policies.dat modern_out.txt
python3 ../spike/verify.py legacy_out.txt modern_out.txt schema.json --lang=en
```
