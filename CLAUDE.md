# CLAUDE.md — ghi chú cho agent làm việc trên repo này

Đọc hết trước khi sửa bất cứ thứ gì. Ngắn là cố ý.

---

## Đây là cái gì

Một công cụ **so sánh kết quả của job xử lý theo lô trước và sau migration**, và
**phân loại** từng khác biệt thành: bỏ qua được, cần ký duyệt, hay chặn go-live.

Nó không dịch mã. Nó không review mã. Nó chỉ trả lời một câu: *hai hệ thống này có
cho ra cùng kết quả không, và chỗ nào khác thì khác vì cái gì.*

---

## Sự thật mà agent sẽ đoán sai nếu không đọc

- **Chưa có khách hàng nào. Chưa có doanh thu. Đây vẫn là spike, chưa là sản phẩm.**
  Hai kịch bản trong `spike/` chạy trên **dữ liệu do chính chúng sinh ra**. Đừng viết
  câu nào ngụ ý đã dùng trên dữ liệu thật. `spike/KET-QUA.md` ghi rõ giới hạn — giữ
  nguyên, đừng làm mềm đi.

- **Giá trị nằm ở `classify.py`, không nằm ở phần còn lại.** `records.py`, `report.py`
  và `verify.py` là đường ống: ai viết cũng vậy. Tỷ lệ 158 dòng đường ống / 48 dòng
  phân loại là **con số phải giữ cho khỏi trôi** — phân loại phình lên nghĩa là đang
  nhét luật riêng của khách vào, và lúc đó đây là tư vấn chứ không phải sản phẩm.

- **Không có luật nào được nhắc tới nghiệp vụ của khách.** Luật phân loại chỉ được
  dựa vào **kiểu dữ liệu**: số thập phân, số nguyên, chuỗi, ngày. Khoảnh khắc trong
  `classify.py` xuất hiện chữ "lãi suất", "bảo hiểm", "tài khoản" là khoảnh khắc sản
  phẩm chết. Thứ riêng của khách thuộc về **lược đồ** (`schema*.json`), không thuộc
  về mã.

- **Số nguyên không có dung sai. Vĩnh viễn.** Đây là luận điểm trung tâm:
  *đừng tìm tiền sai, hãy tìm nguyên nhân sai.* Tiền là kết quả và có dung sai làm
  tròn để nấp sau; số ngày, cờ trạng thái, số lần lặp là nguyên nhân và không có chỗ
  nấp. Trong kịch bản 1, hai lỗi thật chỉ lệch 0,08 và 0,02 ở cột tiền — chúng bị bắt
  **chỉ vì** `accrual_days` lệch 1. Thêm dung sai cho trường số nguyên là xoá sạch lý
  do tồn tại của công cụ.

- **Bộ kiểm thử phải chứng minh được là nó biết fail.** Cả sản phẩm này *là* một bộ
  kiểm thử. Một bộ kiểm thử không bao giờ đỏ thì vô giá trị, và ở đây nó còn là lời
  nói dối bán cho khách. Vì vậy `tests/mutate.py` tồn tại và **phải pass trước mỗi
  commit** — xem mục Lệnh.

- **Dữ liệu khách hàng không bao giờ vào repo.** Không commit, không dán vào issue,
  không để trong thư mục làm việc quá lúc cần. `.gitignore` chặn `customer/` và
  `*.cust.txt` nhưng `.gitignore` không phải cơ chế bảo mật — thói quen mới là.

- **Chưa viết mã sản phẩm.** `personal-brand/tech/migration-verification-ke-hoach.md`
  mục 6 ghi: không viết dòng mã sản phẩm nào cho tới khi có tín hiệu từ ngoài (một
  khách hỏi, hoặc phản hồi từ bài viết). Sửa spike cho đúng và sửa hạ tầng kiểm thử
  thì được; dựng tính năng mới thì không. Nếu định thêm tính năng, **hỏi trước**.

---

## Bố cục

```
CLAUDE.md          Tệp này — SOUL của repo
README.md          Giới thiệu
spike/             Spike: hai kịch bản, công cụ, kết quả, bài viết, ảnh gallery
  classify.py        PHÂN LOẠI — phần duy nhất có giá trị thật
  records.py         đường ống: đọc tệp, ghép bản ghi theo khoá
  report.py          đường ống: in báo cáo (song ngữ vi/en)
  verify.py          đường ống: ghép lại + mã thoát cho CI
  schema*.json       lược đồ — nơi duy nhất chứa thứ riêng của khách
  generate*.py       sinh dữ liệu thử cho kịch bản 1 và 2
  make_gallery.py    dựng ảnh cho listing Upwork, số liệu lấy từ công cụ
  KET-QUA.md         kết quả đo, và các giới hạn đã biết
tests/             Bộ kiểm thử + bộ kiểm thử của bộ kiểm thử
  run.py             115 kiểm tra, không cần pytest
  mutate.py          kiểm chứng ngược: bộ test có thật sự biết fail không
scripts/
  profile_file.py    tệp lạ của khách -> schema.json nháp (+ model cục bộ)
  snapshot.sh        ảnh chụp mỗi giờ, vào nhánh `snapshots`
  weekly-review.md   soát Chủ nhật, 20 phút
harness/           Sub-agent và skill của repo; `install.sh` chép vào .claude/
customer/          Dữ liệu khách — KHÔNG BAO GIỜ commit, đã nằm trong .gitignore
```

Ranh giới cần tôn trọng:

- `classify.py` **không được import** `records.py` hay `report.py`. Nó nhận giá trị
  đã được đọc sẵn và trả về phán quyết. Giữ nó cô lập để còn đo được và còn thay
  được.
- `schema*.json` là **giao diện với khách hàng**. Thêm một khoá vào lược đồ là một
  quyết định sản phẩm, không phải một lần refactor.
- `make_gallery.py` **lấy số liệu trực tiếp từ công cụ**, không gõ tay. Ảnh quảng
  cáo không bao giờ được nói khác với cái công cụ thật sự làm.

---

## Định tuyến: việc nào cho ai

Repo này sẽ phải xử lý tệp khách hàng hàng trăm nghìn tới hàng triệu dòng. Đọc
một tệp như vậy vào context của mô hình đắt tiền là vừa tốn tiền vừa vô ích — nó
không cần dòng thứ 400.000, nó cần biết tệp có **hình dạng** gì.

| Việc | Giao cho | Vì sao |
|---|---|---|
| Đọc / tóm tắt tệp dữ liệu lớn | sub-agent `bulk-reader` (model rẻ) | chỉ cần nén, không cần suy luận |
| Suy ranh giới cột, kiểu, khoá | `scripts/profile_file.py` | **đếm, không đoán** — không mô hình nào ở đây |
| Đặt tên cột cho lược đồ nháp | mô hình **chạy cục bộ**, tuỳ chọn | dữ liệu khách không được rời máy |
| Sửa luật phân loại, thiết kế, viết test | mô hình chính | đây là chỗ sai thì hỏng sản phẩm |
| Phán quyết một khác biệt là lỗi hay không | **`classify.py`, không phải mô hình nào cả** | phán quyết phải tất định và lặp lại được |

Dòng cuối là dòng quan trọng nhất. Một mô hình ngôn ngữ **không bao giờ** được
quyết định một khác biệt có chặn go-live hay không. Khách mua sự tất định: cùng
hai tệp thì cùng một câu trả lời, hôm nay và sáu tháng nữa. Mô hình nằm quanh
sản phẩm để làm việc buồn tẻ, nó không nằm trong đường ra quyết định.

Cài sub-agent và skill: `bash harness/install.sh`.

### Mô hình chạy cục bộ

`scripts/profile_file.py --name` gọi Ollama (11434), LM Studio (1234) hoặc
llama.cpp (8080) ở `localhost`. Không có máy chủ nào thì nó vẫn ra lược đồ, chỉ
là tên trường thành `field_00`.

**Chỉ `localhost`, và đây là ràng buộc sản phẩm chứ không phải tuỳ chọn.** Lý do
không phải tiết kiệm tiền: listing bán hàng hứa dữ liệu khách không rời khỏi mạng
của họ. Thêm một endpoint đám mây vào tệp đó là phá đúng lời hứa đang dùng để
bán. Nếu cần mô hình mạnh hơn, chạy mô hình mạnh hơn trên máy đó.

---

## Lệnh

Chạy từ gốc repo. Không có phụ thuộc ngoài, Python chuẩn.

```bash
python3 tests/run.py              # 115 kiểm tra
python3 tests/mutate.py           # kiểm chứng ngược — BẮT BUỘC trước mỗi commit
python3 tests/mutate.py -v --only classify.py    # soi một tệp
bash scripts/snapshot.sh          # ảnh chụp công việc đang dở
bash harness/install.sh           # cài sub-agent + skill vào .claude/

# tệp lạ của khách -> lược đồ nháp
python3 scripts/profile_file.py <tệp> [lần-chạy-thứ-2-của-hệ-CŨ] [--name] [--out schema.json]

# chạy hai kịch bản spike
cd spike
python3 generate.py  && python3 verify.py legacy_output.txt modern_output.txt schema.json
python3 generate2.py && python3 verify.py legacy2.txt     modern2.txt     schema2.json
python3 verify.py legacy_output.txt modern_output.txt schema.json --lang=en
python3 make_gallery.py           # dựng lại 3 ảnh gallery
```

**`tests/run.py` và `tests/mutate.py` phải xanh trước mọi commit.** Cái thứ hai quan
trọng hơn cái thứ nhất: nó là thứ duy nhất chứng minh cái thứ nhất có ý nghĩa.

---

## Quy ước

- **Vanilla everything.** Không framework, không pytest, không `node_modules`, không
  `requirements.txt`. Thêm một phụ thuộc cần lý do nặng hơn việc khách chạy được công
  cụ trên máy của họ mà không phải xin phép bộ phận bảo mật.
- **Chú thích giải thích *vì sao*, không giải thích *cái gì*.** Mã nói cái gì rồi.
  Chú thích đáng giá nhất trong repo này là các đoạn ghi lại **đánh đổi đã biết** —
  xem cuối `classify.py`.
- **Giới hạn phải được viết ra, không được giấu.** Tệp `KET-QUA.md` có một mục dành
  riêng cho những gì spike **chưa** chứng minh. Khi thêm năng lực mới, thêm cả giới
  hạn mới của nó.
- **Song ngữ.** Tài liệu và chú thích tiếng Việt; chuỗi báo cáo và tài sản bán hàng
  tiếng Anh. Viết theo ngôn ngữ tệp đang dùng.
- **Commit mô tả *vì sao*, thể mệnh lệnh, mỗi commit một mối quan tâm.**
- **Không rewrite lịch sử, không force-push.**

---

## Đột biến sống sót, đã xét và chấp nhận

`tests/mutate.py` hiện bắt **60/62**. Hai con sống sót là **tương đương về ngữ
nghĩa** — chúng làm mã chạy khác đi nhưng không làm kết quả khác đi — nên viết
test để giết chúng chỉ tạo ra test khoá cứng chi tiết nội bộ. Ghi ra đây thay vì
để trôi:

- **`verify.py:71` — vô hiệu hoá `if a == b: continue`.** Bỏ bước thoát sớm thì
  hai dòng giống hệt nhau vẫn đi tiếp vào `classify_field`, và hàm đó trả `None`
  cho mọi trường bằng nhau. Kết quả y hệt, chỉ chậm hơn.
- **`verify.py:74` — `or` thành `and` trong `if ra is None or rb is None`.**
  `parse_trailer` trả `None` khi và chỉ khi lược đồ thiếu `trailer_fields`, mà
  hai bên dùng chung một lược đồ. Không bao giờ có trường hợp đúng một bên là
  `None`, nên `or` và `and` cho cùng kết quả.

Nếu sau này `parse_trailer` trả `None` vì lý do khác (dòng trailer hỏng chẳng
hạn), con thứ hai **thôi tương đương** và phải viết test cho nó.

---

## Bẫy

- Sửa `classify.py` mà quên chạy `mutate.py` là cách êm ái nhất để bộ test mục ruỗng.
  Một luật phân loại mới không có mutation tương ứng thì coi như chưa được kiểm thử.
- `generate*.py` dùng seed cố định. Đổi seed là đổi toàn bộ số liệu trong
  `KET-QUA.md`, `linkedin-post.md` và ảnh gallery. Đổi thì phải cập nhật cả ba.
- Nới dung sai để "bớt nhiễu" luôn có vẻ hợp lý lúc đang nhìn một báo cáo dài. Đó
  chính xác là cách công cụ này biến thành `diff`.
