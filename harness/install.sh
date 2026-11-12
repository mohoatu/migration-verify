#!/usr/bin/env bash
# Cài sub-agent và skill của repo vào `.claude/` của máy này.
#
#   bash harness/install.sh
#
# Vì sao không để thẳng trong `.claude/`: thư mục đó là cấu hình của **máy**, còn
# `harness/` là tài sản của **repo**. Tách ra thì repo mang theo được, và ai
# clone về cũng cài được một lệnh.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p .claude/agents .claude/skills
cp harness/agents/*.md .claude/agents/
cp -r harness/skills/* .claude/skills/

echo "đã cài:"
ls .claude/agents/ | sed 's/^/  agent: /'
ls .claude/skills/ | sed 's/^/  skill: /'
echo
echo "Khởi động lại Claude Code để nó đọc được."
