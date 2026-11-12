#!/usr/bin/env bash
# Ảnh chụp công việc đang dở, vào một nhánh riêng.
#
#   bash scripts/snapshot.sh            # một lần
#   watch -n 3600 bash scripts/snapshot.sh   # mỗi giờ
#
# Vì sao có tệp này: khi để agent sửa mã, thứ đáng sợ không phải nó làm sai —
# mà là nó làm sai rồi mình không quay lại được điểm trước đó. Snapshot không
# phải backup; nó là **nút hoàn tác** cho một phiên làm việc dài.
#
# Snapshot đi vào nhánh `snapshots`, KHÔNG đi vào nhánh đang làm. Lịch sử chính
# vẫn sạch, mỗi commit vẫn một mối quan tâm.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "chưa phải repo git — chạy: git init"; exit 1
fi

if [ -z "$(git status --porcelain)" ]; then
  echo "không có gì thay đổi, bỏ qua"; exit 0
fi

# Chặn dữ liệu khách lọt vào snapshot. `.gitignore` đã chặn, nhưng snapshot là
# thứ chạy tự động không ai nhìn, nên nó phải tự kiểm tra lần nữa.
if git status --porcelain | grep -qE '(^..\s+|/)customer/|\.(cust|prod)\.txt'; then
  echo "DỪNG: có tệp trong customer/ đang chờ commit. Không snapshot."; exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
STAMP=$(date '+%Y-%m-%d %H:%M')
TREE=$(git stash create "wip") || true
[ -z "${TREE:-}" ] && TREE=$(git rev-parse HEAD)

PARENT=$(git rev-parse --verify -q refs/heads/snapshots || true)
if [ -n "$PARENT" ]; then
  COMMIT=$(git commit-tree "$TREE^{tree}" -p "$PARENT" -m "snapshot $STAMP ($BRANCH)")
else
  COMMIT=$(git commit-tree "$TREE^{tree}" -m "snapshot $STAMP ($BRANCH)")
fi
git update-ref refs/heads/snapshots "$COMMIT"

echo "đã chụp $STAMP -> snapshots ($(git rev-parse --short "$COMMIT"))"
echo "xem lại:  git log --oneline snapshots | head"
echo "lấy lại:  git checkout snapshots -- <đường dẫn tệp>"
