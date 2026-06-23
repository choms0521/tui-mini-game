# Battleship 개발 계획서

작성일: 2026-06-23
대상 저장소: `tui-mini-game`
근거 문서: [`docs/game-candidates.md`](../../game-candidates.md) · [`docs/plans/tier1-games-plan.md`](../tier1-games-plan.md)
티어: 2순위
폴더: `battleship/` · 브랜치: `feat/game-battleship`

> 공통 구현 규약(불변 상태, 주입 RNG, 렌더 분리, 영어 식별자, 파일 경계)은
> [`tier1-games-plan.md` §2](../tier1-games-plan.md)를 따른다. 본 문서는 게임 고유 스펙만 다룬다.

## 1. 개요

- **장르**: 추론 보드 + AI
- **재사용 진법**: Minesweeper의 그리드 렌더/커서 이동을 **듀얼 그리드**로 확장
- **한 줄 소개**: 가려진 적 함대를 사격으로 추적해 모두 격침하면 승리.
- **재미 포인트**: 명중·격침의 추적 쾌감과 운의 긴장감. 한 판이 짧고 AI 전략에 따라 체감 난이도가 크게 바뀐다.

## 2. 규칙

- 10x10 격자 2개. 사람 vs AI가 번갈아 한 발씩 사격한다.
- 함대(표준): Carrier(5) · Battleship(4) · Cruiser(3) · Submarine(3) · Destroyer(2), 총 5척 17칸.
- 함선은 가로/세로로만 배치하며 서로 겹치지 않는다(인접 허용; 변형 규칙은 옵션).
- 사격 결과: **miss / hit / sunk**(해당 함선의 모든 칸 명중). 이미 쏜 칸은 다시 쏠 수 없다.
- 먼저 상대 함대 5척을 모두 격침한 쪽이 승리한다.

## 3. 재사용 자산

- Minesweeper `render.py`의 `_pad`/격자 렌더와 커서 강조를 좌(내 함대)·우(추적판) **두 보드**로 복제.
- 좌표/인접 헬퍼는 Minesweeper `board.py`의 `Pos`/경계 검사 패턴을 따른다.

## 4. 상태 모델 (`@dataclass(frozen=True)`)

```
Ship       = (name: str, cells: frozenset[Pos], horizontal: bool)
GameState:
  player_ships:  tuple[Ship, ...]
  ai_ships:      tuple[Ship, ...]
  player_shots:  frozenset[Pos]     # 사람이 적 보드에 쏜 칸
  ai_shots:      frozenset[Pos]     # AI가 내 보드에 쏜 칸
  ai_hunt:       tuple[Pos, ...]    # AI target 모드의 후보 큐(결정성 위해 명시 보관)
  cursor:        Pos                # 추적판 위 조준 위치
  current_turn:  int                # PLAYER / AI
  game_over:     bool
  winner:        int | None
```

- 명중/격침 여부는 `shots`와 `ships`로 매 프레임 유도(파생 상태를 저장하지 않음).

## 5. AI 전략

- **hunt 모드**: 미사격 칸 중 체커보드(parity) 우선으로 무작위 선택(주입 RNG로 결정적).
- **target 모드**: 명중이 나면 인접 4칸을 큐에 넣고, 두 번째 명중부터는 명중 직선 방향을 우선 추적.
- 함선 격침이 확정되면 해당 함선 주변 칸을 큐에서 제거하고 hunt로 복귀.

## 6. 입력

- `화살표`: 추적판 커서 이동
- `Enter`/`Space`: 조준 칸 사격
- `r`: 새 게임 · `q`: 종료

## 7. 렌더

- 좌측 "MY FLEET": 내 함선(블록) + AI 사격(명중 빨강 `X`, 빗맞음 `·`).
- 우측 "TRACKING": 내 사격 결과만(명중/빗맞음), 함선 위치는 비공개. 커서 강조.
- 격침된 함선은 강조색 처리. 패널에 남은 함선 수(양측), 턴 표시, 승/패 배너.

## 8. 셀프테스트 필수 항목

- 함선 배치: 경계 내, 겹침 0, 길이/척수 정확.
- 사격 판정: hit는 hit로, miss는 miss로 기록되고 동일 칸 재사격은 무효(상태 불변).
- 격침 판정: 한 함선의 모든 칸 명중 시 sunk.
- 승리 판정: 적 함선 전부 격침 시 `game_over` + `winner`.
- AI는 항상 미사격 칸(합법 수)을 반환.
- AI target 모드: 명중 직후 다음 사격이 그 명중 칸에 인접.
- 배치·AI 모두 주입 RNG로 결정적.
- 불변성: 전이가 원본 상태를 변형하지 않음.

## 9. 브랜치 & PR

- 브랜치 `feat/game-battleship`, base `main`.
- PR 본문: 규칙 + 조작법 + 셀프테스트 결과(테스트 플랜).

## 10. 리스크 & 완화

| 위험 | 영향 | 완화 |
| --- | --- | --- |
| 듀얼 그리드 레이아웃이 좁은 터미널에서 겹침 | 중 | 두 보드 사이 고정 간격 + 최소 폭 안내 메시지 |
| AI가 너무 약/강해 재미 저하 | 중 | parity hunt + target 추적의 균형, 셀프테스트로 target 동작 고정 |
| target 큐 상태가 비결정적이면 테스트 흔들림 | 중 | 큐를 상태에 명시 보관하고 RNG 주입 |

## 11. 완료 기준

- [ ] `battleship/`에 규약대로 파일 구성(`game.py`/`board.py`/`render.py`/`main.py`/`selftest.py`/`meta.json`/`run.sh`)
- [ ] `selftest.py` 공유 venv 파이썬으로 통과(exit 0)
- [ ] 헤드리스 임포트 스모크 통과
- [ ] 브랜치 푸시 + PR 생성, 본문에 조작법 + 테스트 플랜 포함
