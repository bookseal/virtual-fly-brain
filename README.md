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
.venv/bin/python -m pytest -q
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

공개 비교표는 학습 seed 11·29·47의 같은 온라인 행동량(10,240회·20,480회)을 따로 비교합니다. 각 경로의 초기 정책과 새로운 조건 30회 결과도 분리합니다. 평가 JSON의 `source_version`은 당시 코드의 해시와 경로를 가리킵니다. 공개 manifest의 `reproduction_sources`에서 정확한 소스 파일 목록을, `demonstrations`에서 시범 배열과 seed 구분을 확인할 수 있습니다. 소스 스냅샷은 원본 바이트와 SHA-256 일치를 검사한 뒤 공개합니다.

## 수치 오류 복구와 별도 진단

시뮬레이터의 `PhysicsError`는 생물학적 넘어짐과 구분합니다. `physics_error_policy: terminate`를 명시한 실행은 마지막 유효 관찰값으로 해당 에피소드를 종료하고, 별도의 실패 보상과 재현용 행동열을 기록합니다. 다른 예외는 숨기지 않습니다. 정책은 optimizer 업데이트마다 저장하고, 중간 체크포인트에서 재개할 때에도 요청한 행동 수를 넘지 않도록 첫 rollout 길이를 조정합니다. 중단된 에피소드와 미완료 rollout은 이어 붙이지 않습니다.

초기 체크포인트의 환경 난수도 명시적으로 초기화합니다. 이전 회차의 일부 step-zero 파일에는 예약된 seed가 환경 RNG에 아직 적용되지 않은 문제가 있었으므로, 그 기록은 유지하되 엄밀하게 같은 학습 난수를 쓴 비교로 해석하지 않습니다. 각 평가의 시작 seed는 별도로 명시되어 있어 해당 평가 결과는 보존합니다.

`lab.noise_ablation`은 이 수정 이후 새 대조군과 변경군을 각각 생성합니다. 초기 Gaussian 탐험 표준편차만 1.0과 약 0.368로 다르게 설정하고, 다른 초기 정책 가중치와 환경 RNG를 검사한 증거를 남깁니다. 두 학습 seed의 2,048회·10,240회 고정 평가와 별도 30회 검증을 표에 나눠 표시합니다. `lab.generalization`의 넓은 먹이 위치 평가는 추가 학습 없이 수행하는 별도 진단이며, 가까운 위치의 성적과 합치지 않습니다.

```sh
.venv/bin/python -m lab.noise_ablation runs/YOUR_RUN_ID
```

보조 실험은 주 실험의 상태·최근 평가를 덮어쓰지 않으며, 주 실험 2 worker와 보조 실험 2 worker를 함께 사용하는 범위로 실행합니다. 이미 실행 중인 보조 실험과 겹쳐 직접 실행하지 마세요. 요약 영상, 관찰과 해석, 원본 결과는 모두 같은 연구 노트에 연결됩니다.

연구자의 선택에도 `#experiments?run=RUN_ID&decision=DECISION_ID`로 직접 연결할 수 있습니다. ‘같은 먹이, 다른 선택’에서는 저장된 원본 평가 두 개를 불러와 같은 seed와 먹이 위치를 짝짓고, 측정 경로를 0.05초 단위로 재생합니다. 새로운 시뮬레이션이나 보간으로 만든 경로가 아닙니다.

별도 `lab.compatibility_probe`는 FlyGym 2.1의 CPU API와 렌더링 호환성을 확인합니다. 기존 학습 환경을 업그레이드하지 않으며, 이 프로브의 고정 신호 보행을 학습 성공률과 섞지 않습니다. 가상 시간 1초의 보행을 세 번 측정하고 설치·초기 실행·렌더 시간을 나눠 기록합니다. 몸·제어기와 초기 안정화 방식이 달라 두 버전의 시간을 같은 과제의 성능 배수로 해석할 수 없습니다. 공개 `compatibility/flygym2/` 아래의 원본 JSON과 각 `requirements.lock.txt`를 확인하세요.

`lab.policy_probe`는 시뮬레이터를 돌리지 않고 저장된 모델에 가정 입력을 넣습니다. 거리 1.5/3/7 mm, 방향 −40~40도, 속력 0/6/12 mm/s의 153가지 조합에서 평균 행동과 제어기에 전달되는 신호를 계산합니다. 웹의 ‘모델 출력’ 조절기는 이 표를 탐색합니다. 실제 방문 상태, 경로, 성공률과 구분하며, 입력 인코딩이 기존 환경과 같은지와 행동 범위 변환을 검사합니다.
