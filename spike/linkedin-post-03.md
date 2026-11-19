# Bài 3 — viết bằng từ vựng của thị trường

Soạn **18/11/2026**, sau đợt research. Ba thay đổi so với hai bài trước:

1. **Dùng chữ của họ**: `bug-for-bug compatible`, `parallel run`,
   `differential testing`. Không dùng "migration verification" — không ai tìm
   bằng cụm đó.
2. **Chất liệu mạnh hơn**: kịch bản 3 là hai chương trình độc lập, khác biệt
   **không ai gieo vào**. Hai bài trước kể về khác biệt tự cấy.
3. **Kết bằng câu hỏi về việc giữ tài trợ**, không phải về công cụ. Research
   cho thấy nỗi đau người ta nói ra nhiều nhất là *"làm sao chứng minh với sếp
   rằng dự án đang tiến triển"* — chứ không phải *"làm sao biết bản mới đúng"*.

---

## Bản A — LinkedIn (≈380 từ)

**Two engineers read the same spec. 354 records disagreed. Neither of them was wrong.**

The hard part of a legacy rewrite is not writing the new code. It is being
bug-for-bug compatible with a system nobody fully understands any more — and
proving it before anyone will let you cut over.

I wanted to know what that actually looks like, so I ran it.

I wrote a batch job the way they really exist: a Perl script from about 2004,
one file, no tests, interest and instalment calculations. Then I wrote a
business specification from it — the kind of document a migration team is
actually handed. Then I reimplemented the job in Java 21, working only from
that document.

Same 1,200 input records. Two outputs.

`diff` reported **2,402 changed lines**. 578 records were byte-identical. A
field-level comparison found **354 records where the money was genuinely
different** — and every single one of them came from **one sentence that was
missing from the spec**.

Rule 5 said "the instalment amount is the total divided by the number of
instalments." Rule 6 said "any remainder goes onto the last instalment." The
report has one instalment column. The spec never said which one to print.

Perl printed the last instalment. Java printed the standard one. Both
implementations are a correct reading of the document. Nobody made a mistake,
and nobody would have caught it in code review — the two programs were never
read side by side.

There was a second one. The control total at the foot of the file came out as
59,629,808.34 in Perl and 59,629,808.35 in Java. One cent, after 1,200 records,
from floating-point accumulation. That is the first number an auditor checks.

Here is the part I did not expect. Two of the differences were **0.08 and 0.02**
in the money column — well inside any sane rounding tolerance, and I needed that
tolerance to suppress 275 harmless ones. By money, they were invisible. What
caught them was an **integer** field being off by exactly 1.

Money is an output, and outputs have tolerance to hide behind. Day counts,
status flags, loop counters and tier codes are the causes, and they have no
tolerance at all.

So: give your money columns a tolerance if you must. Give your integers none.

**A question for anyone who has run a long parallel run — how do you show your
sponsor that the rewrite is converging, rather than just that it isn't done
yet?**

---

## Bản B — ngắn, để trả lời trong thread (≈130 từ)

Dùng khi gặp người đang hỏi về rewrite / bug-for-bug compatibility. Trả lời,
không chào hàng.

> On bug-for-bug compatibility: I ran this as an experiment recently. Wrote a
> 2004-style Perl batch job, wrote a business spec from it, then reimplemented
> it in Java from the spec alone.
>
> 1,200 records in. `diff` gave 2,402 changed lines; 578 records were identical;
> 354 had genuinely different money. All 354 came from a single sentence missing
> from the spec — the report had one instalment column and the document never
> said whether that meant the standard instalment or the adjusted last one. Both
> implementations read the document correctly.
>
> The thing that made them findable was not the money column. Two of them were
> off by 0.08 and 0.02, inside any rounding tolerance. They surfaced because an
> integer day-count field was off by exactly 1. Money is an output and has
> tolerance to hide behind; counts and flags are causes and have none.

---

## Đăng ở đâu

**LinkedIn** — bản A. Kèm ảnh `spike/gallery/2-report.png` (đầu ra thật).

**Hacker News** — không đăng bài mới. Thay vào đó **trả lời** bằng bản B khi có
thread về legacy rewrite, COBOL, strangler fig, hay differential testing. Tra
thread mới bằng:
`https://hn.algolia.com/api/v1/search_by_date?query=legacy+rewrite&tags=comment`

**Reddit** — r/ExperiencedDevs và r/dataengineering, bản B, chỉ khi có người hỏi
trước.

Nguyên tắc: **không mở thread để bán.** Chỉ trả lời chỗ đã có người hỏi. Đó là
tham gia cuộc nói chuyện, không phải tiếp thị — và nó hợp với người hướng nội.

---

## Những gì bài viết KHÔNG nói, và vì sao

- **Không nhắc công cụ, không có liên kết, không mời dùng thử.** Chưa có ai hỏi
  mua; quảng cáo lúc này chỉ làm bài mất sức. Ai quan tâm sẽ vào trang cá nhân.
- **Không nói "tôi giúp bạn migrate an toàn".** Đó là câu ai cũng nói.
- **Không giấu rằng đây là thí nghiệm tự dựng.** Bài nói rõ là mình tự viết cả
  hai bản. Người đọc kỹ sẽ nhận ra, và tự nhận trước thì đáng tin hơn bị phát
  hiện.
