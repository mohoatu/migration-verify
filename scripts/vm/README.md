# Máy ảo Windows — **ĐÃ DỪNG 13/11/2026**

Thư mục này giữ lại một nỗ lực **không dùng tới**. Giữ chứ không xoá, vì nó trả
lời sẵn vài câu hỏi tốn thời gian, và vì lúc nào đó có khách thật thì sẽ cần
lại.

> **Trạng thái: dừng.** VM đã xoá, `D:\VMs` đã dọn. Các script còn nguyên và
> chạy được. Tệp ISO giữ lại ở `D:\iso` (8,4 GB) vì Microsoft giới hạn số lần
> tải theo IP — tải lại không hề dễ.

---

## Vì sao dựng, và vì sao dừng

**Mục đích ban đầu** là để agent thao tác tự do mà không đụng máy thật, sau khi
có vài lần em phải nhờ Trung chạy lệnh tay.

**Mục đích đó đã được giải bằng cách khác**: Desktop Commander cho một shell
thật trên máy. Xoá tệp, chạy PowerShell, chạy test trên Windows thật — làm được
hết, không cần VM. Chính nhờ nó mà ngày 12/11 bắt được lỗi `cp1252` khiến
`verify.py` chết khi in báo cáo tiếng Việt trên Windows.

**Giá trị còn lại của VM là cô lập dữ liệu khách hàng** — và **chưa có khách
nào**. Dựng hạ tầng cho một nhu cầu chưa tồn tại đúng là sai lầm đã giết app
Atlassian trước đó.

Cú đánh cuối: VirtualBox chạy **ốc sên** trên máy này (xem dưới), nên cái VM đổi
lấy hai tiếng chờ sẽ là một máy chậm mà không ai muốn dùng.

---

## Những gì đã kiểm, để lần sau khỏi mò lại

### Windows 11 Home **không bật được Hyper-V**, dù gói có trên đĩa

Các gói `Microsoft-Hyper-V-*` nằm sẵn trong `C:\Windows\servicing\Packages` và
`vmcompute.exe` có trong System32 — nhìn thì tưởng bật được. Nhưng:

```
dism /online /enable-feature /featurename:Microsoft-Hyper-V-All /all
  -> Error: 0x800f080c  Feature name Microsoft-Hyper-V-All is unknown.
```

Danh sách tính năng thật của image (build 26200):

```
VirtualMachinePlatform              | Enabled
HypervisorPlatform                  | Enabled
Microsoft-Windows-Subsystem-Linux   | Disabled
```

Không có dòng nào tên Hyper-V, cũng không có Windows Sandbox.

**Bài học: hỏi `dism /online /get-features` trước.** Đừng suy từ việc tệp có tồn
tại, và cũng đừng suy từ kiến thức chung kiểu "Home thì không có gì".

### VirtualBox chạy "snail execution mode" vì VBS đang bật

Log của chính VirtualBox:

```
HM: HMR3Init: Attempting fall back to NEM: AMD-V is not available
NEM: NEMR3Init: Snail execution mode is active!
NEM: VirtualBox is not able to run at its full potential in this execution mode.
```

VBS/Core Isolation giữ AMD-V, nên VirtualBox phải đi qua Windows Hypervisor
Platform. Cài Windows 11 chạy **~1,1%/phút** — khoảng 90 phút chỉ riêng phần
chép tệp.

Muốn nhanh thì phải **tắt Core Isolation / Memory Integrity**, tức hạ bảo mật
máy chính. Không đáng cho một nhu cầu chưa có.

### Các API của VBoxManage 7.2 dễ đoán sai

| Đoán sai | Đúng |
|---|---|
| `modifyvm --secure-boot on` | không tồn tại; và nó làm **cả lệnh `modifyvm` fail**, VM giữ nguyên cấu hình mặc định |
| `modifynvram ... secureboot --enable` ngay | phải `inituefivarstore` → `enrollmssignatures` → **`enrollorclpk`** → rồi mới `secureboot --enable` |
| `--hostname=win11-verify` | phải là FQDN: `win11-verify.local` |
| `--post-install-command="ps1 ... -Online ..."` | chuỗi có dấu cách bị PowerShell 5.1 băm nát; **chép thành tệp rồi chạy bằng đường dẫn** |

### PowerShell `ErrorActionPreference='Stop'` coi stderr của native tool là lỗi chí mạng

`controlvm poweroff` trên một VM đã tắt ghi ra stderr → script chết ở bước dọn
dẹp. Mọi bước được phép thất bại phải bọc lại và nói rõ.

### Sai lầm tốn nhiều thời gian nhất là của chính em

Đặt hạn chờ 45 phút rồi **bỏ mặc không nhìn**. Hết giờ, script báo lỗi, rồi em
tắt VM **khi nó đang cài dở** — đó là lý do ổ ảo có 5,3 GB dữ liệu mà không có
bootloader, và em đi chẩn đoán nhầm sang "mẫu answer file không khớp build mới".

Chụp một ảnh màn hình ở phút thứ 3 đã trả lời đúng câu hỏi đó. Hơi mỉa mai với
một dự án mà luận điểm là *đừng tìm triệu chứng, hãy tìm nguyên nhân*.

---

## Nếu dựng lại (khi có khách thật)

```
scripts\vm\00-get-iso.ps1     # ISO + verify SHA256 với hash Microsoft công bố
scripts\vm\02-create-vm.ps1   # tạo VM + cài Windows unattended
scripts\vm\03-guest-setup.ps1 # bật SSH, cài Python, chép repo, chạy test
scripts\vm\guest\enable-ssh.ps1
```

Các script đã sửa hết những lỗi ở trên và chạy được — lần chạy cuối đã cài tới
23% bình thường trước khi dừng chủ động.

Hai việc nên làm khác đi lần sau:

1. **Chụp màn hình theo chu kỳ (3, 8, 15 phút)** thay vì đặt hạn giờ rồi bỏ mặc.
   `VBoxManage controlvm <vm> screenshotpng <file>`.
2. **Quyết trước về Core Isolation.** Không tắt thì chấp nhận ốc sên; tắt thì
   nhanh gấp mấy lần nhưng hạ bảo mật máy chính. Đừng khám phá điều này ở phút
   thứ 60.

Và câu hỏi nên hỏi trước tiên: **đã có khách chưa?** Nếu chưa thì Desktop
Commander là đủ.
