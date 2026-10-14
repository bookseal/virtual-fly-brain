# Fly Brain Lab — 계획 (2026-10-11 작성)

목표: 초파리 "몸"(MuJoCo)과 "뇌"(커넥톰)를 Mac 한 대에서 굴려 보고, 초파리가 게임(지렁이, 마리오 코스)을 **학습하는 장면**을 영상으로 남긴다.
모든 명령·설명·결과는 http://localhost:8765 타임라인에 실시간 기록한다.

## 환경 결론 (Phase 0 조사 결과)
- Mac M1 Pro, 16 GB, GPU 없음 → MuJoCo(CPU 물리)는 OK, RL은 "작은 정책 + 고수준 행동"으로 설계.
- 몸 모델 후보 비교:
  | | flygym-gymnasium 1.3.2 (legacy) | flygym 2.1.0 (2026-03 재작성) | flybody (DeepMind) |
  |---|---|---|---|
  | Python | 3.10–3.12 (3.13 불가) | 3.12–3.14 | 3.10 + conda |
  | 냄새·시각·먹이 아레나·틈/블록 지형 | **있음** (OdorArena, Gapped/Blocks/MixedTerrain) | 미확인(재작성으로 일부 제외 추정) | 없음 |
  | 걷기+회전 컨트롤러 | HybridTurningController (2D 하강 신호) | 4d turning controller 튜토리얼 있음, CPU 10x 빠름 | RL로 직접 학습 필요(수십 GPU·일 단위) |
  | 선택 | **1차 선택: 게임 재료가 전부 있음** | 속도 병목 시 대체 | 비교·참고용 |
- Eon Systems 뇌-몸 폐루프 코드는 공개 흔적 없음 → Phase 6은 Shiu 모델 + VFB로 축소 재현.

## Phase 별 계획 (v2: 7시간 스프린트, 토큰 창 끝까지 전부 사용)
| P | 내용 | 산출물 | 시간 |
|---|---|---|---|
| 0 | 환경 점검, 계획, 타임라인 사이트 | PLAN.md, localhost:8765 | 21:15~21:45 ✅ |
| 1 | VFB MCP 등록 + JSON-RPC 직접 호출(도구 목록, 뉴런 경로 질의). 2026-09-03 Cell 수컷 CNS 커넥톰 소식 해설을 사이트에 기록 | 질의/응답, 📌노트 | ~22:30 |
| 2 | `uv venv -p 3.12` → flygym-gymnasium 설치 → 첫 렌더 영상 → 시뮬 속도 측정 | fly_first.mp4, 속도표 | ~23:30 |
| 3 | HybridTurningController에 (좌,우) 하강 신호 → 규칙 기반 냄새 추적으로 먹이 도달 | odor_taxis.mp4 | ~00:30 |
| 4 | 🐛 지렁이 게임: 먹이 먹으면 재생성+점수. PPO, SubprocVecEnv 8개, 백그라운드 학습. 곡선 20분마다 갱신 | learning_curve.png, snake_before/after.mp4 | 01:30 시작, 03:30 종료 |
| 5 | 🍄 마리오 코스: 틈·블록 지형 사이드스크롤 + 측면 카메라, 규칙 기반 통과 → 시간 남으면 RL 조향 | mario_course.mp4 | ~02:30 |
| 6 | 뇌→몸: 커넥톰에서 회전 하강뉴런 조회, 발화율→하강 신호 매핑 데모 | brain2body.mp4 | ~03:30 |
| 7 | 마무리: 결과 모음, 튜토리얼 정리 | 사이트 최종본 | ~04:30 |

## 설계 원칙
- 각 Phase는 RL 없이 규칙 기반으로 영상 하나를 먼저 뽑고, 그다음 RL로 교체한다.
- 학습은 2시간 안에 끝나야 한다 → 속도 측정 뒤 RL 결정 주기·스텝 예산을 정한다. 느리면 flygym 2.x로 몸만 교체.
- 사이트의 모든 명령어에는 한 줄씩 한글 직역을 붙인다(명령어 직역 표).
