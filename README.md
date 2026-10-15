# Fly Brain Lab

생물학을 처음 배우는 개발자를 위한 초파리 학습 실험실입니다. DNA·RNA·단백질부터 뉴런과 제어를 인터랙티브 모션과 퀴즈로 배우고, 실제 3D 초파리 몸의 강화학습 과정을 시간순으로 따라갑니다.

**[공개 사이트 열기](https://bookseal.github.io/virtual-fly-brain/)**

- 상태 → 정책 → 행동 → 보상 → 업데이트를 설명하는 SVG 모션
- 설치·실패·수정·평가를 담은 10분 단위 실험 노트
- 실제 FlyGym/MuJoCo 행동 영상과 이동 경로
- HyperFrames로 만든 구간별 영상과 시간별 회고
- 무작위·규칙·학습 전·학습 후 정책의 같은 조건 비교
- 다섯 입문 수업, 객관식 퀴즈, 용어 사전

공개 사이트는 **저장된 실험 결과의 스냅샷**입니다. 화면에 공개 시각과 당시의 상태를 표시합니다. 실제 학습은 로컬 컴퓨터에서 실행하며, 새 공개 스냅샷을 커밋하면 GitHub Actions가 Pages를 다시 배포합니다.

## 로컬에서 공개 사이트 보기

Python 표준 라이브러리만 있으면 됩니다.

```sh
git clone https://github.com/bookseal/virtual-fly-brain.git
cd virtual-fly-brain
python3 scripts/export_public.py --build _site
python3 -m lab.server --directory _site
```

브라우저에서 http://localhost:8765/ 를 엽니다. 프로젝트 하위 경로에서도 영상과 원본 기록을 열 수 있도록 상대 경로를 사용합니다.

## 실험의 범위

3D 몸은 FlyGym의 기존 관절 보행 제어기로 움직이며, PPO는 **어디로 움직일지 고르는 좌우 신호**를 학습합니다. 먹이의 상대 좌표를 입력으로 알려 주는 과제입니다. 실제 초파리 뇌 전체나 생물학적 가소성의 재현을 주장하지 않습니다.

학습과 평가 seed를 분리하고, 같은 시작 조건의 고정 평가와 선택에 사용하지 않은 조건의 최종 평가를 구분합니다. 2D 단순 이동 모델이 사용되면 3D 결과와 따로 표시합니다. 학습이 개선되지 않거나 기록이 지연된 구간도 남깁니다.

- `lab/`: 환경, PPO 학습·평가, 체크포인트, 기록기, 영상 큐
- `site/`: 정적 웹 UI와 입문 학습
- `public/`: 공개용 실험 기록·영상·설정·체크포인트
- `video/interval-template/`: 반복 사용한 HyperFrames 구성 템플릿
- `scripts/export_public.py`: 로컬 기록을 공개용으로 내보내고 Pages를 빌드
- `tests/`: 기록 지연, 렌더 실패, 프로세스 중단·재개와 재현 시험

각 평가 JSON에 설정, seed, 실제 행동과 경로를 보존합니다. 체크포인트 ZIP에는 정책과 optimizer가 포함됩니다. 시뮬레이션 실행에는 Python 3.12와 다음 의존성이 필요합니다.

```sh
uv venv --python 3.12
uv pip sync --python .venv/bin/python requirements.lock.txt
.venv/bin/python -m lab.learning --help
```

HyperFrames를 다시 렌더하려면 `video/`에서 `npm ci`로 고정된 버전을 설치합니다. 영상 템플릿의 한국어 글꼴과 GSAP는 로컬 자산을 사용합니다.

## 기록 공개와 배포

로컬 원본 `runs/`, 개인 인계 문서, 계정 사용량과 인증 정보는 Git에 포함하지 않습니다. 공개 내보내기는 개인 경로와 계정 사용량을 제거하고, 이미 확보된 실험 자료를 복사합니다. 원본 로컬 기록은 그대로 유지합니다.

```sh
python3 scripts/export_public.py --run runs/YOUR_RUN_ID --build _site
git add public
git commit -m "Update public experiment snapshot"
git push
```

`main`에 push하면 `.github/workflows/pages.yml`이 정적 사이트를 빌드하고 GitHub Pages에 배포합니다. GitHub Pages에서는 Python 학습 프로세스를 실행하지 않습니다.

## 검증

```sh
.venv/bin/python -m pytest -q tests/test_lab.py
FLY_UI_BASE=http://localhost:8765 NODE_PATH=/path/to/node_modules node scripts/check-ui.cjs
FLY_UI_BASE=http://localhost:8765 NODE_PATH=/path/to/node_modules node scripts/check-experiments.cjs
```

브라우저 검사는 Playwright와 Chrome을 사용합니다. 공개 배포에는 프로젝트 하위 경로, 영상 재생, 스냅샷 표시, 원본 JSON과 보고서 링크를 별도로 검증합니다.

## 출처

이 저장소는 독립적인 학습 프로젝트입니다. Virtual Fly Brain의 공식 서비스는 [virtualflybrain.org](https://www.virtualflybrain.org/)이며, 실제 몸과 학습 도구는 [FlyGym](https://github.com/NeLy-EPFL/flygym-gymnasium), [MuJoCo](https://github.com/google-deepmind/mujoco), [Stable-Baselines3](https://github.com/DLR-RM/stable-baselines3)를 사용합니다. 영상은 [HyperFrames](https://github.com/heygen-com/hyperframes)로 구성합니다. 외부 라이브러리와 글꼴은 각 프로젝트의 라이선스를 따릅니다.

## 두 번째 회차: 참여형 연구 다큐

연구 기록은 질문 → 관찰 → 해석 → 다음 선택 순서로 보존합니다. 고정 신호 5종의 실제 3D 보정 영상, 예상 선택 퀴즈, 원문을 확인한 기술 노트가 실험 타임라인과 연결됩니다. 주소의 `#experiments?run=RUN_ID&interval=INTERVAL_ID`로 특정 기록을 공유할 수 있습니다.

이번 비교는 원래 제어 신호 범위 `[-0.5, 1.5]`를 유지하면서 정책 출력 `[-1, 1]`에 `0.5`를 더해 전달합니다. 예전 모델은 `raw` 설정으로 재생해야 합니다. PPO 단독과 규칙 시범 모방 후 PPO를 동일한 환경·온라인 학습량으로 비교하며, 모방 수집량은 별도로 셉니다. 시범은 실제 3D 몸에서 수집하고, 학습·시범 검증·정책 평가 seed를 분리합니다.

`.venv/bin/python -m lab.start_day2 --start`는 새 회차 설정을 만들고 기록·시범 수집·비교·공개 프로세스를 시작합니다. 미완료 회차가 있으면 중복 실행을 막습니다. 아래 명령은 이미 생성된 회차 설정을 대상으로 합니다.

```sh
.venv/bin/python -m lab.campaign_v2 runs/YOUR_RUN_ID
.venv/bin/python -m lab.recorder runs/YOUR_RUN_ID
.venv/bin/python -m lab.video runs/YOUR_RUN_ID
.venv/bin/python -m lab.publisher runs/YOUR_RUN_ID
```

기록기는 10분, 공개기는 30분 주기로 동작합니다. 공개기는 별도 detached checkout에서 검증한 `public/` 자료만 커밋·push하고, 실제 Pages manifest 반영을 확인합니다. 개발 중인 코드를 자동으로 커밋하지 않습니다. 로컬 개발 checkout이 자동 공개 커밋보다 뒤처졌다면, 개발 커밋을 만든 뒤 `git fetch origin`과 `git rebase origin/main`으로 먼저 합칩니다. 충돌 시 강제 push하지 않습니다.

대화가 끊겨도 로컬 프로세스는 계속됩니다. 자동 진행은 미리 정한 규칙이며, GPT가 계속 분석하고 있다는 뜻은 아닙니다. 노트북 절전·프로세스 종료·네트워크 장애로 생긴 공백은 공개 기록에 표시합니다. `runs/YOUR_RUN_ID/STOP` 파일을 만들면 학습이 안전 경계에서 중단됩니다. 최종 회고 렌더와 공개 확인까지 끝난 뒤 프로세스가 종료됩니다.
