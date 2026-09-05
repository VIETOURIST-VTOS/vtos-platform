#!/usr/bin/env bash
# Mỗi file test dùng một CSDL SQLite riêng → chạy từng tiến trình để không lẫn dữ liệu demo.
set -e
cd "$(dirname "$0")/.."
rm -f test_*.db
for f in tests/test_*.py; do python -m pytest -q "$f"; done
rm -f test_*.db
