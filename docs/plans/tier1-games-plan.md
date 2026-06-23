# 1순위 게임 3종 개발 계획서

작성일: 2026-06-23
대상 저장소: `tui-mini-game`
근거 문서: [`docs/game-candidates.md`](../game-candidates.md)
범위: 1순위 3종 (Mastermind · Connect Four · Sudoku)

## 1. 목표와 진행 방식

`docs/game-candidates.md`에서 1순위로 선정된 3종을 기존 진법 그대로 구현한다. 세 게임은 서로 공유 로직이 없는 독립 폴더이므로 **병렬 개발**한다.

- 게임마다 **별도 git 워크트리 + 별도 브랜치**에서 동시 진행한다.
- 각 작업은 구현 → 셀프테스트 통과 → 커밋 → 브랜치 푸시 → **PR 자동 생성**까지 처리한다.
- 게임 폴더는 런처가 `meta.json`으로 자동 발견하므로 런처 코드 수정은 불필요하다.
- `README.md` 게임 표 갱신은 세 PR이 모두 합류된 뒤 **일괄 정리**한다(브랜치 간 충돌 방지).

## 2. 공통 구현 규약

모든 신규 게임은 기존 게임(`snake/`, `sokoban/`, `wordle/`, `minesweeper/`)과 동일한 구조를 따른다.

### 파일 구성

| 파일 | 역할 | 비고 |
| --- | --- | --- |
| `game.py` | 불변 게임 상태 + 순수 전이 함수 | `@dataclass(frozen=True)`, `dataclasses.replace` |
| `board.py` | 격자 상수/기하 헬퍼 (선택) | 순수 함수, 그리드 게임에 권장 |
| `render.py` | blessed 트루컬러 렌더 | `draw(term, state, ...)`, 깜빡임 없는 전체 프레임 1회 출력 |
| `main.py` | blessed 입력 루프 (엔트리) | `snake/main.py` 패턴: `fullscreen/cbreak/hidden_cursor`, `_map_key`, dirty 플래그, `run()` |
| `solver.py` | 탐색/풀이 로직 (선택) | `sokoban/solver.py` 패턴 (Sudoku 전용) |
| `selftest.py` | 헤드리스 자동 테스트 | `python selftest.py`로 실행, 통과 시 exit 0 |
| `meta.json` | 런처 등록 메타 | `{"name", "description", "entry": "main.py"}` |
| `run.sh` | 실행 래퍼 | `snake/run.sh` 복사, 게임명만 교체, `chmod +x` |

### 핵심 원칙

- **불변성**: 상태는 절대 변형하지 않고 `replace`로 새 객체를 만든다.
- **결정적 무작위**: 무작위가 필요하면 `random.Random` 인스턴스를 주입해 테스트를 결정적으로 유지한다.
- **렌더 분리**: 게임 로직(`game.py`)은 blessed에 의존하지 않는다. blessed 의존은 `render.py`/`main.py`에만 둔다.
- **언어**: 코드 주석/문자열/식별자는 표준 기술 영어. 한자(중국어 문자) 일절 금지.
- **파일 경계**: 각 작업은 **자기 게임 폴더 안의 파일만** 생성/수정한다. `README.md`, `play.sh`, `launcher/`, `requirements.txt`, 다른 게임 폴더는 건드리지 않는다.

### 검증

- 셀프테스트를 공유 venv 파이썬으로 실행해 통과(exit 0)를 확인한 뒤에만 커밋한다.
  - 공유 venv 경로: `/Users/mscho/development/games/mini-game/.venv/bin/python`
  - 워크트리에는 `.venv`가 없으므로 위 절대 경로를 사용한다(없으면 `python3 -m venv .venv && .venv/bin/pip install blessed`로 임시 구성).
- blessed UI 루프는 대화형이므로 셀프테스트로만 검증하고, 헤드리스 임포트 스모크까지 확인한다.

## 3. 브랜치 & PR 전략

| 게임 | 폴더 | 브랜치 | PR 제목 |
| --- | --- | --- | --- |
| Mastermind | `mastermind/` | `feat/game-mastermind` | `feat: add Mastermind terminal game` |
| Connect Four | `connect_four/` | `feat/game-connect-four` | `feat: add Connect Four terminal game` |
| Sudoku | `sudoku/` | `feat/game-sudoku` | `feat: add Sudoku terminal game` |

각 PR 본문에는 게임 설명 + 조작법 + 테스트 플랜(셀프테스트 결과)을 포함한다. base 브랜치는 `main`.

## 4. 게임별 상세 스펙

### 4.1 Mastermind

- **장르**: 추론 퍼즐 / 재사용 진법: Wordle 추측-피드백 루프
- **규칙**: 비밀 코드는 색 4칸, 색 종류 6가지. 플레이어는 최대 10회 추측. 매 추측마다 피드백 산출:
  - **exact**: 색과 위치가 모두 맞은 칸 수
  - **partial**: 색은 코드에 있으나 위치가 틀린 칸 수
  - 산출식: 색별로 `min(secret 개수, guess 개수)` 합 − exact. (중복 색 처리가 최대 난관 — 셀프테스트로 집중 검증)
- **상태 모델** (`@dataclass(frozen=True)`): `secret: tuple[int,...]`, `guesses: tuple[tuple[int,...],...]`, `feedbacks: tuple[tuple[int,int],...]`, `current: tuple[int,...]`(작성 중 행), `max_guesses: int`, `game_over: bool`, `won: bool`
- **입력**: 숫자 `1~6` 색 선택, `←/→` 또는 `Backspace`로 편집, `Enter` 제출, `r` 재시작, `q` 종료
- **렌더**: 과거 추측 + 피드백(검은/흰 페그) 누적, 현재 입력 행, 색마다 고유 트루컬러, 승/패 배너
- **셀프테스트 필수 항목**:
  - 중복 색 포함 피드백 정확도(예: secret=AABB, guess=ABBC 등 경계 케이스)
  - 모든 칸 exact 시 승리 판정
  - 최대 횟수 소진 시 패배 판정
  - 중복으로 인한 partial 과다 계산이 없음
  - 비밀 코드는 주입 RNG로 결정적 생성

### 4.2 Connect Four

- **장르**: 보드 + AI / 재사용 진법: Minesweeper 그리드 렌더 + 미니맥스 탐색
- **규칙**: 7열 6행. 사람 vs AI. 열을 고르면 말이 가장 아래 빈칸으로 낙하. 가로/세로/대각선 4목 완성 시 승리. 보드가 가득 차면 무승부.
- **AI**: 알파-베타 가지치기 미니맥스, 깊이 제한(예: 5). 평가 함수는 길이 4 윈도우 점수화. 동률 수는 주입 RNG로 tie-break(결정적 테스트 위해 시드 고정).
- **상태 모델** (`@dataclass(frozen=True)`): `board: tuple[tuple[int,...],...]`(0=빈칸,1/2=플레이어), `current_player: int`, `game_over: bool`, `winner: int | None`(0=무승부), `last_move: int | None`
- **입력**: `←/→` 열 선택, `Enter`/`Space`/`↓` 낙하, `r` 재시작, `q` 종료
- **렌더**: 격자 + 빨강/노랑 트루컬러 말, 현재 선택 열 표시기, 승/무 배너
- **셀프테스트 필수 항목**:
  - 4방향(가로·세로·대각선 2종) 승리 판정
  - 가득 찬 열 거부
  - 보드 가득 시 무승부 판정
  - AI가 항상 합법 수 반환
  - AI가 즉시 승리 수를 잡고 상대의 즉시 승리를 차단(기초 전술)
  - 보드 불변성(전이가 원본을 변형하지 않음)

### 4.3 Sudoku

- **장르**: 두뇌 퍼즐 / 재사용 진법: Minesweeper 그리드 + 커서, Sokoban `solver.py`
- **규칙**: 9x9. 유일해를 가진 퍼즐을 난이도별(주어진 칸 수)로 생성. 플레이어가 빈칸을 1~9로 채워 완성.
- **생성기/풀이** (`solver.py`):
  - 백트래킹 풀이기(무작위 순서) → 완전해 1개 생성
  - 칸 제거 시 유일해 유지(해 개수 ≤ 1) 확인하며 난이도 목표까지 제거
  - 유일해 검사는 2개째 해를 찾는 즉시 중단(early-exit)해 속도 확보
- **상태 모델** (`@dataclass(frozen=True)`): `givens: tuple[tuple[int,...],...]`(고정 칸, 0=비움), `grid: tuple[tuple[int,...],...]`(현재 입력), `solution: tuple[tuple[int,...],...]`, `cursor: tuple[int,int]`, `won: bool`
- **입력**: `화살표` 커서 이동, `1~9` 입력, `0`/`Backspace`/`Space` 지움, `r` 새 퍼즐, `q` 종료 (givens 칸은 수정 불가)
- **렌더**: 9x9 격자 + 3x3 박스 구분선, givens/사용자 입력 색 구분, 커서 강조, 충돌 칸 강조, 완성 배너
- **셀프테스트 필수 항목**:
  - 풀이기가 알려진 퍼즐을 알려진 해로 정확히 해결
  - 유일해 검사기: 적정 퍼즐은 정확히 1, 제약 부족 퍼즐은 2 이상 반환
  - 생성 퍼즐이 유일해를 가지며 풀이 가능
  - 행/열/3x3 박스 유효성 검사
  - 충돌 칸 탐지
  - `grid == solution`일 때 승리 판정
  - 주입 RNG로 결정적 생성, 셀프테스트는 빠르게 유지

## 5. README / 런처 후처리

- 런처(`launcher/`)는 각 게임의 `meta.json`을 자동 발견하므로 별도 등록 작업이 없다.
- `README.md`의 게임 표는 세 PR 합류 후 한 번에 3행을 추가한다(브랜치 간 충돌 방지).

## 6. 검증 기준 (완료 정의)

- [ ] 각 게임 폴더에 규약대로 파일 구성 완비
- [ ] `selftest.py` 공유 venv 파이썬으로 통과(exit 0)
- [ ] 헤드리스 임포트 스모크 통과(모듈 임포트 오류 0건)
- [ ] 각 게임 브랜치 푸시 + PR 생성 완료
- [ ] PR 본문에 조작법 + 테스트 플랜 포함

## 7. 다음 단계 (2순위 6종)

1순위 3종 검증 후, 동일 방식으로 2순위 6종을 병렬 진행한다.

> Battleship · Reversi · Gomoku · Tron · Frogger · Blackjack
