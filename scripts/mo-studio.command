#!/bin/bash
# Double-click in Finder: start the local service (if it is not running) and open the Studio page.
# Keep this Terminal window open while using Studio or app.html; close it to stop the service.
cd "$(dirname "$0")/.." || exit 1
URL="http://127.0.0.1:8000/studio"

if curl -fs -o /dev/null --max-time 2 http://127.0.0.1:8000/health; then
  echo "Studio đang chạy sẵn, mở trình duyệt…"
  open "$URL"
  exit 0
fi

if [ ! -x .venv/bin/uvicorn ]; then
  echo "Chưa cài đặt. Mở Terminal trong thư mục dự án và chạy:"
  echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements-demo.txt"
  read -r -p "Nhấn Enter để đóng."
  exit 1
fi

echo "Đang bật Studio… (giữ cửa sổ này mở, đóng cửa sổ là tắt Studio)"
( for _ in $(seq 1 30); do
    if curl -fs -o /dev/null --max-time 1 http://127.0.0.1:8000/health; then open "$URL"; break; fi
    sleep 1
  done ) &
exec .venv/bin/uvicorn --app-dir backend app.creator_main:app --host 127.0.0.1 --port 8000
