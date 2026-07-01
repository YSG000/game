# SKILL — 반복 작업 실행법 (런북)

> "손을 움직일 때" 그대로 따라 하는 절차서. 명령/순서를 복붙해서 쓴다.
> 위치 기준: 모든 파일은 `C:\CL\test1` 안에 있음.

## 1. 서버 켜기 (호스트가 순위 받으려면 필수)
1. `C:\CL\test1\서버_켜기.bat` 더블클릭
2. 검은 창이 뜨면 **닫지 말고 유지** (닫으면 서버 꺼짐)
3. 브라우저에서 `http://localhost:8000` 접속

수동 실행:
```powershell
cd C:\CL\test1
python leaderboard_server.py
```

## 2. 서버 끄기
```powershell
# 8000 포트를 잡고 있는 프로세스 종료
foreach ($c in (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) {
  Stop-Process -Id $c.OwningProcess -Force
}
```

## 3. 부서원에게 공유하기 (같은 네트워크)
1. 호스트에서 서버 켜두기 (위 1번)
2. 호스트 IP 확인:
   ```powershell
   (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like '192.168.*'}).IPAddress
   ```
3. 부서원에게 **주소만** 전달 → `http://<호스트IP>:8000`
   (⚠️ HTML 파일을 나눠주면 저장 안 됨 — 주소로 접속해야 순위 저장됨)

## 4. 게임/서버 수정 후 반영
- **HTML 수정**: 브라우저에서 `Ctrl+F5` (캐시 새로고침)
- **서버(.py) 수정**: 서버 끄고(2번) 다시 켜기(1번)

## 5. GitHub Pages 재배포
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cd C:\CL\test1
Copy-Item memory_daily_prototype.html index.html -Force   # 배포본 갱신
git add .
git commit -m "update"
git push
```
- 저장소: `https://github.com/YSG000/game`
- 공개 주소: `https://ysg000.github.io/game/`
- 404 뜨면 Pages 빌드 중 → 1~2분 후 새로고침

## 6. 순위 기록 초기화
```powershell
Set-Content C:\CL\test1\scores.json "[]" -Encoding UTF8
```

## 게임 주소 (서버 켠 뒤)
| 경로 | 화면 |
|---|---|
| `/` | 게임 선택 허브 |
| `/memory` | 오늘의 기억 (격자 기억) |
| `/idiom` | 사자성어 도전 (4지선다) |

## API 참고
| 메서드 | 경로 | 동작 |
|---|---|---|
| GET | `/api/scores?game=memory\|idiom` | 게임별 기록(JSON 배열). game 미지정 시 memory |
| POST | `/api/score` | `{game, name, score, age, mode}` 제출 → 게임·사람·모드별 최고점 갱신 |

> `game` 필드 없는 기존 기록은 자동 `memory`로 취급(하위호환).
