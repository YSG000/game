# -*- coding: utf-8 -*-
"""
오늘의 기억 — 부서 순위표 서버
--------------------------------
어제 빠졌던 파이썬 서버입니다. 설치 없이 표준 라이브러리만 사용합니다.

실행:  python leaderboard_server.py
접속:  http://localhost:8000  (같은 와이파이의 다른 기기는 http://<이 PC IP>:8000)

게임 HTML(memory_daily_prototype.html)을 함께 서빙하고,
점수는 같은 폴더의 scores.json 에 누적 저장합니다.
사람·모드별로 "최고 점수" 한 개만 유지합니다.
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "memory_daily_prototype.html")
DATA_FILE = os.environ.get("SCORES_FILE", os.path.join(BASE_DIR, "scores.json"))

_lock = threading.Lock()


def load_records():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_records(records):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def upsert(records, name, score, age, mode):
    """사람(name) + 모드(mode)별 최고 점수만 유지."""
    name = (name or "익명").strip()[:12] or "익명"
    mode = mode if mode in ("normal", "hard") else "normal"
    score = max(0, min(1_000_000, int(score)))
    age = max(0, min(200, int(age)))

    for r in records:
        if r.get("id") == name and (r.get("mode") or "normal") == mode:
            if score > r.get("best", 0):
                r["best"] = score
                r["bestAge"] = age
            r["plays"] = r.get("plays", 0) + 1
            r["last"] = _now_ms()
            return r
    rec = {"id": name, "mode": mode, "best": score, "bestAge": age,
           "plays": 1, "last": _now_ms()}
    records.append(rec)
    return rec


def _now_ms():
    import time
    return int(time.time() * 1000)


class Handler(BaseHTTPRequestHandler):
    # 콘솔 로그 간소화
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_html(self):
        try:
            with open(HTML_FILE, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            self.send_response(500)
            self.end_headers()
            self.wfile.write("memory_daily_prototype.html 을 찾을 수 없습니다. 같은 폴더에 두세요."
                             .encode("utf-8"))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/memory_daily_prototype.html"):
            self._send_html()
        elif self.path.startswith("/api/scores"):
            self._send_json(200, load_records())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/api/score":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            body = {}

        with _lock:
            records = load_records()
            upsert(records,
                   body.get("name"), body.get("score", 0),
                   body.get("age", 0), body.get("mode", "normal"))
            save_records(records)
            self._send_json(200, records)


def _safe_print(msg):
    """윈도우 한국어 콘솔(cp949)에서도 죽지 않게 안전하게 출력."""
    try:
        print(msg)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(msg.encode(enc, errors="replace").decode(enc, errors="replace"))


def main():
    # 콘솔 인코딩을 UTF-8로 (가능한 환경에서). 실패해도 무시.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    _safe_print("=" * 56)
    _safe_print("  오늘의 기억 - 부서 순위표 서버")
    _safe_print("=" * 56)
    _safe_print(f"  접속(이 PC):   http://localhost:{PORT}")
    _safe_print(f"  같은 네트워크: http://<이 PC의 IP>:{PORT}")
    _safe_print(f"  점수 파일:     {DATA_FILE}")
    _safe_print("  (이 창을 닫으면 서버가 꺼집니다.)")
    _safe_print("=" * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
        server.shutdown()


if __name__ == "__main__":
    main()
