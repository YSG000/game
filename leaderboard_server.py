# -*- coding: utf-8 -*-
"""
두뇌 게임 허브 — 부서 순위표 서버
--------------------------------
설치 없이 표준 라이브러리만 사용합니다.

실행:  python leaderboard_server.py
접속:  http://localhost:8000  (같은 와이파이의 다른 기기는 http://<이 PC IP>:8000)

- /                         → 게임 선택 허브
- /memory                   → 오늘의 기억 (격자 기억 게임)
- /idiom                    → 사자성어 4지선다 게임
- GET  /api/scores?game=X   → 게임별 순위(JSON 배열). game 미지정 시 memory.
- POST /api/score           → {game,name,score,age,mode} 제출. 사람·모드·게임별 최고점 유지.

점수는 같은 폴더의 scores.json 에 누적 저장합니다.
game 필드가 없는 기존 기록은 자동으로 'memory' 로 취급합니다(하위호환).
"""

import json
import os
import sys
import threading
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.environ.get("SCORES_FILE", os.path.join(BASE_DIR, "scores.json"))

# 경로 → 파일 매핑
MEMORY_FILE = "index.html"   # 오늘의 기억 게임 (GitHub Pages 진입점 겸용)
IDIOM_FILE = "game.html"     # 사자성어 스피드퀴즈
PAGES = {
    "/": "hub.html",
    "/hub": "hub.html",
    "/memory": MEMORY_FILE,
    "/index.html": MEMORY_FILE,
    "/memory_daily_prototype.html": MEMORY_FILE,  # 옛 이름 하위호환
    "/SHdev.html": MEMORY_FILE,                    # 옛 이름 하위호환
    "/idiom": IDIOM_FILE,
    "/game.html": IDIOM_FILE,
    "/idiom.html": IDIOM_FILE,                     # 옛 이름 하위호환
}

GAMES = ("memory", "idiom")

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


def _now_ms():
    import time
    return int(time.time() * 1000)


def upsert(records, name, score, age, mode, game):
    """사람(name) + 모드(mode) + 게임(game)별 최고 점수만 유지."""
    name = (name or "익명").strip()[:12] or "익명"
    game = game if game in GAMES else "memory"
    mode = mode if mode in ("normal", "hard") else "normal"
    score = max(0, min(1_000_000, int(score)))
    age = max(0, min(200, int(age)))

    for r in records:
        if (r.get("id") == name
                and (r.get("mode") or "normal") == mode
                and (r.get("game") or "memory") == game):
            if score > r.get("best", 0):
                r["best"] = score
                r["bestAge"] = age
            r["plays"] = r.get("plays", 0) + 1
            r["last"] = _now_ms()
            return r
    rec = {"id": name, "game": game, "mode": mode, "best": score,
           "bestAge": age, "plays": 1, "last": _now_ms()}
    records.append(rec)
    return rec


class Handler(BaseHTTPRequestHandler):
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

    def _send_file(self, filename):
        path = os.path.join(BASE_DIR, filename)
        try:
            with open(path, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            msg = f"{filename} 을(를) 찾을 수 없습니다. 같은 폴더에 두세요.".encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")  # 수정 즉시 반영
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in PAGES:
            self._send_file(PAGES[path])
        elif path == "/api/scores":
            q = parse_qs(urlparse(self.path).query)
            game = (q.get("game", ["memory"])[0]) or "memory"
            if game not in GAMES:
                game = "memory"
            recs = [r for r in load_records()
                    if (r.get("game") or "memory") == game]
            self._send_json(200, recs)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path != "/api/score":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            body = {}

        game = body.get("game", "memory")
        with _lock:
            records = load_records()
            upsert(records,
                   body.get("name"), body.get("score", 0),
                   body.get("age", 0), body.get("mode", "normal"), game)
            save_records(records)
            # 방금 제출한 게임의 순위만 돌려줌
            recs = [r for r in records if (r.get("game") or "memory")
                    == (game if game in GAMES else "memory")]
            self._send_json(200, recs)


def _safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(msg.encode(enc, errors="replace").decode(enc, errors="replace"))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    _safe_print("=" * 56)
    _safe_print("  두뇌 게임 허브 - 부서 순위표 서버")
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
