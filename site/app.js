'use strict';
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const storageKey = 'fly-brain-learning-v1';
let completed = [], storageAvailable = true;
try { const saved = JSON.parse(localStorage.getItem(storageKey) || '[]'); if (Array.isArray(saved)) completed = [...new Set(saved.filter(n => Number.isInteger(n) && n >= 1 && n <= 5))]; } catch { storageAvailable = false; }
let view = 'learn', chapter = 1, cleanup = () => {}, timeline = null, timelineText = '', timelineError = false;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const sources = {
  rna: ['NHGRI · DNA에서 RNA, 단백질로', 'https://www.genome.gov/about-genomics/fact-sheets/Transcriptome-Fact-Sheet'],
  protein: ['NHGRI · 단백질이란?', 'https://www.genome.gov/genetics-glossary/Protein'],
  neuron: ['NINDS · 뉴런의 구조와 신호 전달', 'https://www.ninds.nih.gov/sites/default/files/2025-05/NINDS_Life_and_Death_of_a_Neuron_Booklet_073024_B_FOR_ONLINE_0.pdf'],
  map: ['Nature (2024) · 성체 초파리 뇌의 연결 지도', 'https://www.nature.com/articles/s41586-024-07558-y'],
  fly: ['NeuroMechFly · 몸과 감각의 시뮬레이션', 'https://neuromechfly.org/'],
  rl: ['Spinning Up · 관찰, 정책, 보상과 강화학습', 'https://spinningup.openai.com/en/latest/spinningup/rl_intro.html'],
  vfb: ['Virtual Fly Brain · 뉴런과 연결 데이터 탐색', 'https://www.virtualflybrain.org/']
};
const lessons = [
  {
    short: '세포의 작업실', sub: 'DNA · RNA · 단백질', tag: 'THE BUILDING BLOCKS', title: '세포 안에서는 누가 일을 할까?',
    intro: '세포를 작은 작업실이라고 생각해 보세요. 그 안에는 <strong>보관된 제작 정보</strong>가 있고, 그 정보를 읽어 만든 <strong>실제 부품</strong>이 있습니다. 생소한 이름 세 개를 이 흐름에 연결하면 됩니다.',
    tags: ['출발점: 세포가 뭔지 알면 충분해요', '핵심 질문: 정보는 어떻게 부품이 될까?'],
    labTitle: 'DNA에서 단백질까지, 직접 한 단계씩', analogyTitle: '저장소 → 작업용 사본 → 작동하는 부품',
    analogy: 'DNA는 오래 보관하는 제작 정보, mRNA는 필요한 부분을 옮겨 적은 작업용 사본에 가깝습니다. 리보솜이라는 조립 장치가 그 사본을 읽고 단백질을 만듭니다. “정보를 읽어 실제 부품을 만든다”는 흐름을 떠올려 보세요.',
    realTitle: '단백질은 영양 성분이면서, 세포의 일꾼입니다',
    real: '단백질은 아미노산이라는 작은 분자들이 이어져 접힌 물질입니다. 물질을 감지하는 수용체, 화학 반응을 돕는 효소, 근육의 움직임에 관여하는 부품도 단백질입니다. 여기서 RNA는 단백질 제작 정보를 운반하는 mRNA를 뜻합니다. 모든 RNA가 단백질로 이어지는 것은 아닙니다.',
    takeaway: 'DNA 자체가 움직이는 게 아니라, 그 정보를 이용해 만든 단백질들이 세포의 일을 합니다.',
    quiz: {q:'세포가 어떤 물질을 감지할 “센서 부품”을 만들었어요. 이 부품에 가장 가까운 것은?', options:['DNA — 제작 정보가 담긴 분자','mRNA — 제작 정보를 옮긴 사본','단백질 — 실제로 물질을 감지하는 부품'], answer:2, feedback:['DNA는 부품 제작에 필요한 정보를 담습니다. 감지하는 일을 맡는 부품과 구분해 보세요.','mRNA는 조립 장치에 정보를 전달합니다. 정보를 읽어 만들어지는 물질이 무엇인지 다시 보세요.','맞아요. 수용체 단백질은 특정 물질과 상호작용해 세포가 신호를 받아들이게 합니다. DNA는 정보, mRNA는 사본, 단백질은 부품이라는 구분입니다.']},
    sources:['rna','protein']
  },
  {
    short: '신호를 보내는 세포', sub: '뉴런 · 시냅스', tag: 'SIGNALS & CONNECTIONS', title: '뉴런도 세포입니다. 특기가 다를 뿐.',
    intro: '<strong>뉴런은 신호를 받아 다른 세포에 전달하는 데 특화된 세포</strong>입니다. 앞에서 본 단백질 중에는 전기를 띤 입자가 드나드는 문처럼 작동하는 것도 있습니다. 이 덕분에 뉴런은 전기적 신호를 만들 수 있습니다.',
    tags:['연결 고리: 단백질이 신호 전달을 도와요','컴퓨터로 떠올리기: 입력을 받는 노드'],
    labTitle:'입력을 키워서 신호를 보내 보세요',analogyTitle:'입력을 모으고, 조건이 되면 이벤트 발생',
    analogy:'입력을 받아 내부 상태가 바뀌는 노드를 떠올려 보세요. 많은 뉴런은 전압 변화가 문턱을 넘으면 짧은 전기 신호인 “활동전위”를 만듭니다. 발화라는 말도 이 신호가 발생한다는 뜻입니다. 발화율은 일정 시간 동안 발생한 신호의 횟수입니다.',
    realTitle:'세포 사이의 접점이 “시냅스”입니다',
    real:'그림은 화학 시냅스를 단순화했습니다. 첫 뉴런의 전기 신호가 말단에 도달하면 신경전달물질이 나와 다음 세포의 수용체에 작용합니다. 그 결과 다음 뉴런이 신호를 내기 쉬워지거나 어려워질 수 있습니다. 모든 뉴런이 단순한 on/off 장치인 것은 아닙니다.',
    takeaway:'뉴런은 노드, 시냅스는 노드 사이 신호 전달 접점. 단, 실제 신호는 전기·화학 작용입니다.',
    quiz:{q:'뉴런 A와 뉴런 B 사이의 “시냅스”는 무엇에 가까울까요?',options:['세포 사이에서 신호가 전달되는 접점','뉴런 안에 보관된 DNA 전체','뇌 전체를 지휘하는 중앙 CPU'],answer:0,feedback:['맞아요. 시냅스는 신호가 다른 세포에 영향을 주는 접점입니다. 연결이 있다고 언제나 다음 뉴런이 발화하는 것은 아닙니다.','DNA는 세포 안의 제작 정보입니다. 시냅스는 두 세포 사이에서 신호가 전달되는 곳입니다.','뇌에는 여러 회로가 함께 작동합니다. 시냅스는 중앙 장치가 아니라 세포 사이의 접점입니다.']},sources:['neuron','protein']
  },
  {
    short:'뇌를 그래프로 보기',sub:'커넥톰 · 연결 지도',tag:'THE BRAIN AS A GRAPH',title:'뇌의 배선도를 데이터로 바꾼다면?',
    intro:'뉴런이 서로 어떻게 연결되는지 기록한 지도를 <strong>커넥톰</strong>이라고 합니다. 컴퓨터 쪽 언어로는 <strong>뉴런을 노드, 연결을 방향 있는 엣지로 표현한 그래프</strong>로 볼 수 있습니다.',
    tags:['연결 고리: 여러 뉴런을 모으면 회로','핵심 질문: 연결만 알면 동작도 알까?'],labTitle:'연결 하나를 끊으면 경로는 어떻게 될까요?',
    analogyTitle:'연결 지도는 그래프 데이터입니다',analogy:'이 그림에서 S는 감각 입력, A와 B는 중간 노드, M은 운동 출력입니다. S에서 M으로 가는 경로를 검색할 수 있습니다. VFB(Virtual Fly Brain)는 실제 초파리 뉴런의 이름, 모양, 연결 자료를 찾는 도구입니다. 이 연습 그림의 S·A·B·M은 실제 뉴런 이름이 아닙니다.',
    realTitle:'배선도를 얻는 것과 뇌를 실행하는 것은 다릅니다',real:'네트워크 토폴로지만으로 서버에서 실행될 프로그램을 알 수 없듯, 연결 지도만으로 행동이 전부 결정되지는 않습니다. 신호의 세기와 시간, 세포 상태, 몸과 환경의 영향도 필요합니다. 연결 수를 곧바로 AI 모델의 학습된 가중치와 같다고 볼 수도 없습니다.',
    takeaway:'커넥톰은 “누가 누구와 연결되어 있나”에 답합니다. “어떻게 작동하나”에는 추가 모델과 실험이 필요합니다.',
    quiz:{q:'초파리 뇌의 연결 지도를 얻었습니다. 지금 할 수 있다고 말해도 되는 것은?',options:['그 초파리의 모든 기억과 행동을 그대로 재생한다','연결 경로를 찾고, 기능에 대한 가설을 세운다','단백질이나 신호의 특성은 더 이상 고려하지 않아도 된다'],answer:1,feedback:['지도만으로 기억과 행동을 그대로 재생할 수는 없습니다. 각 뉴런의 작동 방식과 상태 등 정보가 더 필요합니다.','맞아요. 지도에서 경로를 찾고 “이 경로가 이 행동에 관여할까?”라는 가설을 세울 수 있습니다. 실제 기능은 다른 데이터와 실험으로 확인해야 합니다.','같은 연결도 신호 특성과 상태에 따라 다르게 작동합니다. 구조를 안다는 것과 작동 규칙을 안다는 것은 별개입니다.']},sources:['map','vfb']
  },
  {
    short:'뇌와 몸 연결하기',sub:'감각 → 제어 → 행동',tag:'THE FEEDBACK LOOP',title:'몸이 움직이면, 다음 입력도 달라집니다.',
    intro:'먹이 쪽으로 조금 움직이면 먹이와의 거리도 바뀝니다. 달라진 감각이 다음 행동에 영향을 주죠. 이렇게 <strong>관찰 → 행동 → 새 관찰</strong>이 반복되는 구조를 피드백 루프라고 합니다.',
    tags:['연결 고리: 뇌의 출력이 몸을 움직여요','컴퓨터로 떠올리기: 상태를 갱신하는 반복문'],labTitle:'먹이 위치를 바꾸고, 한 번씩 움직여 보세요',
    analogyTitle:'observe → act → observe, 반복하기',analogy:'이 데모는 먹이의 좌표를 읽고, 그 방향으로 일정 거리 이동하는 규칙입니다. 움직인 뒤에는 현재 위치에서 다시 방향을 계산합니다. 서버가 응답만 보내고 끝나는 구조보다, 센서와 모터를 계속 갱신하는 제어 루프에 가깝습니다.',
    realTitle:'실제 초파리와는 무엇이 다를까요?',real:'여기서는 먹이 좌표를 직접 알려 줍니다. 실제 초파리는 냄새 같은 감각을 이용하고, 근육과 다리도 복잡하게 움직입니다. 프로젝트에서 사용할 몸 시뮬레이터는 관절, 접촉, 물리 법칙을 계산합니다. 이 그림은 흐름을 이해하기 위한 2D 설명용 데모입니다.',
    takeaway:'뇌를 이해하려면 입력과 출력 사이뿐 아니라, 행동이 다음 입력을 바꾸는 순환까지 봐야 합니다.',
    quiz:{q:'초파리가 이동한 뒤에 감각 입력을 다시 읽는 이유는?',options:['이동하면서 몸과 환경의 관계가 바뀌었기 때문','DNA를 매번 새로 만들어야 하기 때문','연결 지도의 노드 이름을 바꾸기 위해서'],answer:0,feedback:['맞아요. 이동하면 먹이까지의 거리와 감각이 바뀝니다. 다음 행동은 바뀐 상태를 바탕으로 정해야 합니다.','한 번의 이동마다 DNA를 다시 만들지는 않습니다. 이 반복문에서 갱신하는 것은 현재 감각과 몸의 상태입니다.','노드 이름을 바꾸는 과정이 아닙니다. 몸이 움직인 뒤 달라진 입력을 읽기 위해 반복합니다.']},sources:['fly']
  },
  {
    short:'이 프로젝트 읽기',sub:'모델 · 규칙 · 학습',tag:'FROM CONCEPT TO PROJECT',title:'이제, 우리가 만들려는 것을 읽어 봅시다.',
    intro:'목표는 <strong>초파리의 연결 자료와 가상 몸을 활용해 행동을 실험하는 것</strong>입니다. 연결 자료를 찾는 단계, 몸을 움직이는 단계, 행동 규칙을 학습시키는 단계는 각각 따로 확인해야 합니다.',
    tags:['연결 고리: 지도 + 작동 규칙 + 몸 + 환경','핵심 질문: 움직이면 곧 학습일까?'],labTitle:'같은 움직임, 다른 제어 방식',
    analogyTitle:'규칙을 작성할 수도, 보상으로 정책을 바꿀 수도',analogy:'규칙 기반 제어는 사람이 “먹이 방향으로 이동” 같은 규칙을 정합니다. 강화학습(RL)은 행동의 결과로 받은 보상을 이용해 행동 선택 방식, 즉 정책을 조정합니다. 움직이는 영상 하나만으로 학습했다는 결론을 내릴 수는 없습니다.',
    realTitle:'인공신경망과 실제 뉴런은 같은 것이 아닙니다',real:'인공신경망의 노드는 계산을 위한 수학적 요소입니다. 실제 뉴런은 단백질을 만들고 에너지를 쓰며 전기·화학적으로 작동하는 세포입니다. 여기서 뇌 모델은 필요한 성질을 골라 계산하는 근사이며, 생명체 전체를 복제했다는 뜻은 아닙니다.',
    takeaway:'규칙으로 움직인 결과, 학습한 결과, 생물학적으로 검증된 결과를 구분해서 읽으면 됩니다.',
    quiz:{q:'가상 초파리가 먹이를 향해 걷는 영상을 보았습니다. 학습 여부를 확인하려면?',options:['움직이기만 하면 학습한 것이므로 확인이 필요 없다','그림이 실제 초파리와 얼마나 닮았는지만 본다','제어 방식과 학습 전후 성능, 평가 조건을 확인한다'],answer:2,feedback:['사람이 작성한 규칙으로도 움직일 수 있습니다. 행동이 보이는 것과 경험으로 정책이 개선된 것은 다릅니다.','겉모습의 정교함은 제어 방식과 별개입니다. 무엇이 업데이트되었고 성능이 개선되었는지를 확인해야 합니다.','맞아요. 어떤 정책을 어떻게 바꾸었는지, 같은 평가 조건에서 전후 성능이 개선됐는지 확인해야 합니다. 생물의 학습을 재현했다는 주장에는 별도의 검증도 필요합니다.']},sources:['map','fly','rl']
  }
];
const terms = [
 ['세포','Cell','생명체를 이루는 기본 단위. 내부에 여러 분자와 구조가 있고, 물질을 바꾸고 에너지를 이용하며 활동합니다.',1],
 ['DNA','DNA','세포를 만들고 유지하는 데 필요한 유전 정보를 담는 분자. “보관된 제작 정보”로 떠올려 보세요.',1],
 ['유전자','Gene','기능을 하는 RNA나 단백질을 만드는 데 관여하는 DNA 구간. DNA 전체와 유전자 하나는 구분합니다.',1],
 ['RNA · mRNA','Messenger RNA','RNA는 여러 역할을 하는 분자입니다. 그중 mRNA는 DNA에서 읽은 단백질 제작 정보를 조립 장치에 전달합니다.',1],
 ['단백질','Protein','아미노산 사슬이 접혀 만들어진 물질. 구조를 지탱하거나, 물질을 감지하거나, 화학 반응을 돕는 등 다양한 일을 합니다.',1],
 ['리보솜','Ribosome','mRNA의 정보를 읽어 아미노산을 이어 주는 세포 안의 조립 장치. RNA와 단백질로 이루어져 있습니다.',1],
 ['뉴런','Neuron','신호를 받아 다른 세포로 전달하는 데 특화된 세포. 신경세포라고도 합니다.',2],
 ['시냅스','Synapse','뉴런이 다른 뉴런이나 근육 같은 세포에 영향을 주는 신호 전달 접점.',2],
 ['신경전달물질','Neurotransmitter','화학 시냅스에서 방출되어 다음 세포의 수용체에 작용하는 물질. 영향을 받는 세포에 따라 효과가 달라집니다.',2],
 ['발화 · 발화율','Spike · Firing rate','발화는 짧은 전기 신호인 활동전위의 발생. 발화율은 일정 시간에 발생한 신호의 횟수입니다.',2],
 ['커넥톰','Connectome','뉴런들이 서로 어떻게 연결되는지 기록한 지도. 연결 구조를 보여 주지만 모든 동작 규칙을 담지는 않습니다.',3],
 ['VFB','Virtual Fly Brain','초파리 신경계의 이름, 모양, 연결 등 연구 자료를 검색하고 탐색하는 서비스.',3],
 ['감각뉴런 · 운동뉴런','Sensory · Motor neuron','감각뉴런은 외부나 몸 안의 자극을 신호로 바꾸고, 운동뉴런은 근육 등에 신호를 전달합니다.',4],
 ['하강뉴런','Descending neuron','뇌에서 몸의 운동을 조절하는 신경계 쪽으로 신호를 보내는 뉴런. “고수준 명령을 아래쪽 제어 회로에 전달한다”는 비유가 도움이 됩니다.',4],
 ['피드백 루프','Feedback loop','행동의 결과가 다음 입력에 반영되는 반복 구조. 관찰 → 행동 → 새 관찰로 이어집니다.',4],
 ['정책 · 강화학습','Policy · Reinforcement learning','정책은 관찰을 바탕으로 행동을 고르는 방식. 강화학습은 보상을 이용해 그 방식을 조정하는 학습 방법입니다.',5],
 ['MuJoCo · FlyGym','Physics engine · Simulation framework','MuJoCo는 물체의 운동과 접촉을 계산하는 물리 엔진. FlyGym은 가상 초파리의 몸과 행동 실험을 위한 도구입니다.',5]
];
function updateNav(){
  $('#lesson-nav').innerHTML = lessons.map((l,i)=>`<a class="lesson-link ${view==='learn'&&chapter===i+1?'active':''} ${completed.includes(i+1)?'complete':''}" ${view==='learn'&&chapter===i+1?'aria-current="step"':''} href="#learn/${i+1}"><span class="number">${completed.includes(i+1)?'✓':String(i+1).padStart(2,'0')}</span><span>${l.short}<small>${l.sub}</small></span></a>`).join('');
  $$('.view-nav a').forEach(a=>{a.classList.toggle('active',a.dataset.view===view);if(a.dataset.view===view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  $('#progress-count').textContent=`${completed.length} / 5`;$('#course-progress').value=completed.length;
  $('#progress-note').textContent=storageAvailable?(completed.length===5?'다섯 개념을 모두 확인했어요. 언제든 복습하세요.':'정답 확인 기록은 이 브라우저에 저장돼요.'):'이 환경에서는 현재 방문 중에만 기록돼요.';
}
function sourceHTML(keys){return `<details class="sources"><summary>더 알아보기 · 설명의 근거와 비유의 범위</summary><p>컴퓨터 비유와 조작 그림은 이해를 돕기 위한 설명입니다. 실제 세포의 형태·비율·시간이나 실험 데이터를 재현하지 않습니다.</p><ul>${keys.map(k=>`<li><a href="${sources[k][1]}" target="_blank" rel="noopener noreferrer">${sources[k][0]} ↗</a></li>`).join('')}</ul></details>`;}
function caption(index,title,body){return `<span class="caption-index">${index}</span><div><b>${title}</b><p>${body}</p></div>`;}
function renderLesson(){
 const l=lessons[chapter-1];
 $('#main').innerHTML=`<div class="breadcrumb"><span>쉽게 배우기 <span>/</span> <b>${l.short}</b></span><span>${String(chapter).padStart(2,'0')} / 05</span></div>
 <section class="chapter-hero"><div class="chapter-tag">CHAPTER ${String(chapter).padStart(2,'0')} · ${l.tag}</div><h1>${l.title}</h1><p class="hero-copy">${l.intro}</p><div class="concept-tags">${l.tags.map(t=>`<span>${t}</span>`).join('')}</div></section>
 <section class="lab" aria-label="${l.labTitle}"><div class="lab-top"><span class="lab-title">${l.labTitle}</span><span class="lab-tag">INTERACTIVE EXPLAINER</span></div><div id="experiment"></div></section>
 <div class="below-lab"><article class="explain-card"><span class="mini-label">COMPUTING ANALOGY</span><h3>${l.analogyTitle}</h3><p>${l.analogy}</p></article><article class="explain-card warm"><span class="mini-label">BACK TO BIOLOGY</span><h3>${l.realTitle}</h3><p>${l.real}</p></article></div>
 <div class="takeaway"><span aria-hidden="true">↳</span><p><b>이것만 가져가세요.</b><br>${l.takeaway}</p></div>
 ${chapter===5?'<div id="project-mini" class="project-mini"></div>':''}
 <section class="quiz" aria-labelledby="quiz-question"><div class="quiz-head">✓ &nbsp; QUICK CHECK <span>· 외우지 말고, 연결해 보세요</span></div><h3 id="quiz-question">${l.quiz.q}</h3><div class="quiz-options">${l.quiz.options.map((o,i)=>`<button class="quiz-option" data-answer="${i}" aria-pressed="false"><span class="quiz-letter">${'ABC'[i]}</span>${o}</button>`).join('')}</div><div class="quiz-feedback" role="status" aria-live="polite"></div></section>
 <div class="lesson-bottom">${chapter>1?`<a class="btn" href="#learn/${chapter-1}">← 이전 이야기</a>`:'<span class="inline-status">순서대로, 또는 궁금한 곳부터.</span>'}<a class="btn primary next" href="${chapter<5?'#learn/'+(chapter+1):'#project'}">${chapter<5?lessons[chapter].short:'실제 프로젝트 기록 보기'} →</a></div>${sourceHTML(l.sources)}`;
 $$('.quiz-option').forEach(b=>b.addEventListener('click',()=>{
  const choice=Number(b.dataset.answer),correct=choice===l.quiz.answer;
  $$('.quiz-option').forEach(x=>{x.classList.remove('correct','wrong');x.setAttribute('aria-pressed','false');});
  b.classList.add(correct?'correct':'wrong');b.setAttribute('aria-pressed','true');
  $('.quiz-feedback').textContent=(correct?'✓ ':'다시 생각해 볼까요? ')+l.quiz.feedback[choice];
  if(correct&&!completed.includes(chapter)){completed.push(chapter);try{localStorage.setItem(storageKey,JSON.stringify(completed));}catch{storageAvailable=false;}updateNav();}
 }));
 [setupCell,setupNeuron,setupGraph,setupLoop,setupProjectLesson][chapter-1]();
}
function svgOpen(label,box='0 0 760 280'){return `<svg viewBox="${box}" role="img" aria-label="${label}"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#a5b5c4"/></marker></defs>`;}
function setupCell(){
 let stage=0,timer=null;
 const rungs=Array.from({length:11},(_,i)=>{const y=77+i*9,dx=Math.sin(i*.7)*21;return `<line x1="${145-dx}" y1="${y}" x2="${145+dx}" y2="${y}" stroke="${i%2?'#ddb693':'#94b5cd'}" stroke-width="3"/><circle cx="${145-dx}" cy="${y}" r="3.5" fill="#739bb8"/><circle cx="${145+dx}" cy="${y}" r="3.5" fill="#d49b70"/>`;}).join('');
 $('#experiment').innerHTML=`<div class="lab-canvas">${svgOpen('세포 안에서 DNA 정보를 mRNA로 옮기고, 리보솜이 단백질을 조립하는 세 단계')}<rect x="22" y="22" width="716" height="237" rx="90" fill="#f1f6f9" fill-opacity=".6" stroke="#d5e1e9" stroke-dasharray="5 5"/><text x="66" y="49" class="svg-tiny">CELL / 세포 안</text>
 <ellipse cx="148" cy="133" rx="81" ry="91" fill="#eaf1f8" stroke="#c8d8e7"/><text x="148" y="201" text-anchor="middle" class="svg-tiny">핵 · 정보 보관</text>
 <g id="dna">${rungs}<text x="145" y="237" text-anchor="middle" class="svg-label">DNA</text></g>
 <path d="M239 125 H312" fill="none" stroke="#a5b5c4" stroke-width="2" marker-end="url(#arrow)"/><text x="276" y="107" text-anchor="middle" class="svg-tiny">전사 · 옮겨 적기</text>
 <g id="rna" class="molecule inactive"><path d="M325 127 Q342 101 358 127 T391 127 T424 127" fill="none" stroke="#d68b56" stroke-width="4" stroke-linecap="round"/>${[331,346,361,376,391,406,421].map((x,i)=>`<line x1="${x}" y1="${120+(i%2)*8}" x2="${x}" y2="${135+(i%2)*8}" stroke="#d68b56" stroke-width="3"/>`).join('')}<text x="375" y="187" text-anchor="middle" class="svg-label">mRNA</text><text x="375" y="207" text-anchor="middle" class="svg-muted">필요한 정보의 사본</text></g>
 <path d="M444 125 H517" fill="none" stroke="#a5b5c4" stroke-width="2" marker-end="url(#arrow)"/><text x="480" y="107" text-anchor="middle" class="svg-tiny">번역 · 조립하기</text>
 <g id="protein" class="molecule inactive"><ellipse cx="541" cy="125" rx="21" ry="28" fill="#e1e9d9" stroke="#aabd99"/><text x="540" y="171" text-anchor="middle" class="svg-tiny">리보솜</text>${Array.from({length:9},(_,i)=>`<circle class="protein-bead" cx="${571+i*12}" cy="125" r="7"/>`).join('')}<text x="622" y="207" text-anchor="middle" class="svg-label">단백질</text><text x="622" y="227" text-anchor="middle" class="svg-muted">접혀서 일하는 부품</text></g></svg></div>
 <p class="diagram-note">초파리 같은 동물 세포의 단백질 제작 흐름을 단순화했습니다. DNA가 사라져서 RNA가 되는 것은 아닙니다.</p>
 <div class="lab-controls"><button class="btn primary" id="cell-play">▶ 흐름 재생</button><div class="steps-control">${['정보 보관','RNA로 옮기기','단백질 만들기'].map((s,i)=>`<button class="step-btn" data-stage="${i}">${i+1}. ${s}</button>`).join('')}</div></div><div class="lab-caption" id="cell-caption" aria-live="polite"></div>`;
 const captions=[['01','DNA · 필요한 제작 정보를 보관합니다','유전자는 DNA의 한 구간입니다. 여기서는 단백질을 만드는 데 쓰일 정보가 담긴 구간을 읽습니다.'],['02','mRNA · 필요한 정보만 작업용으로 옮깁니다','DNA의 정보를 RNA로 옮겨 적는 과정을 전사라고 합니다. 원본 DNA는 남아 있고, mRNA 사본이 만들어집니다.'],['03','단백질 · 정보를 읽어 실제 부품을 조립합니다','리보솜이 mRNA를 읽어 아미노산을 이어 줍니다. 이를 번역이라고 합니다. 만들어진 사슬은 접혀 기능하는 구조를 이룹니다.']];
 function show(n){stage=n;$('#rna').classList.toggle('inactive',n<1);$('#protein').classList.toggle('inactive',n<2);$('#protein').classList.toggle('folded',n===2);$$('.protein-bead').forEach((b,i)=>{b.setAttribute('cx',n===2?622+Math.cos(i*.85)*29:571+i*12);b.setAttribute('cy',n===2?122+Math.sin(i*.85)*25:125);});$$('[data-stage]').forEach(b=>{b.classList.toggle('selected',Number(b.dataset.stage)===n);b.setAttribute('aria-pressed',String(Number(b.dataset.stage)===n));});$('#cell-caption').innerHTML=caption(...captions[n]);}
 function stop(){clearInterval(timer);timer=null;$('#cell-play').textContent='▶ 흐름 재생';}
 $$('[data-stage]').forEach(b=>b.addEventListener('click',()=>{stop();show(Number(b.dataset.stage));}));
 $('#cell-play').addEventListener('click',()=>{if(timer){stop();return;}show(0);$('#cell-play').textContent='Ⅱ 일시정지';timer=setInterval(()=>{show(stage+1);if(stage===2)stop();},1800);});show(0);cleanup=()=>clearInterval(timer);
}
function setupNeuron(){
 let timer=null;
 $('#experiment').innerHTML=`<div class="lab-canvas">${svgOpen('입력과 문턱을 비교하는 뉴런 A, 신호가 전달되는 시냅스, 뉴런 B')}
 <text x="98" y="40" class="svg-muted" text-anchor="middle">입력</text><path d="M45 78 L105 126 M40 139 L105 126 M55 194 L105 126" class="axon"/>
 <circle id="neuron-a" cx="151" cy="126" r="42" fill="#edf3f8" stroke="#b7c8d5" stroke-width="2"/><circle cx="151" cy="126" r="13" fill="#c5d6e5"/><path d="M195 126 H450 M450 126 L476 101 M450 126 L476 151" class="axon"/>
 <path id="signal-travel" class="signal-line flow-off" d="M196 126 H465" fill="none" stroke="#ce6343" stroke-width="5"/>
 <rect x="478" y="69" width="59" height="119" rx="17" fill="#fff3e8" stroke="#eed7c4" stroke-dasharray="4 4"/>
 <g id="transmitters" class="flow-off">${[0,1,2,3,4,5].map(i=>`<circle cx="${490+i%3*15}" cy="${104+Math.floor(i/3)*34}" r="4" fill="#d98953"/>`).join('')}</g>
 <path d="M550 87 L582 127 M546 129 H582 M550 166 L582 127" class="axon"/><circle id="neuron-b" cx="616" cy="127" r="37" fill="#edf3f8" stroke="#b7c8d5" stroke-width="2"/><path d="M654 127 H705" class="axon"/>
 <text x="151" y="209" text-anchor="middle" class="svg-label">뉴런 A</text><text x="318" y="164" text-anchor="middle" class="svg-muted">세포 안: 전기 신호</text><text x="508" y="219" text-anchor="middle" class="svg-label">시냅스</text><text x="508" y="238" text-anchor="middle" class="svg-tiny">이 그림에서는 화학 신호</text><text x="637" y="209" text-anchor="middle" class="svg-label">뉴런 B</text>
 <text id="neuron-readout" x="151" y="243" text-anchor="middle" class="svg-tiny">입력 30 / 문턱 60</text></svg></div>
 <p class="diagram-note">문턱 60은 이해를 돕기 위해 정한 임의의 값입니다. 실제 전압이나 초파리 측정값이 아닙니다.</p>
 <div class="lab-controls"><label class="range-control" for="stimulus">입력 세기 <input id="stimulus" type="range" min="0" max="100" value="30" step="10"><output id="stimulus-value" for="stimulus">30</output><span class="helper">문턱: 60</span></label><button id="send-signal" class="btn primary">신호 보내 보기 →</button></div><div id="neuron-caption" class="lab-caption" aria-live="polite"></div>`;
 function reset(){clearTimeout(timer);$('#signal-travel').classList.add('flow-off');$('#transmitters').classList.add('flow-off');$('#neuron-a').classList.remove('node-active');$('#neuron-b').classList.remove('node-active');}
 function read(){const v=Number($('#stimulus').value);$('#stimulus-value').value=v;$('#neuron-readout').textContent=`입력 ${v} / 문턱 60`;reset();$('#neuron-caption').innerHTML=caption(v>=60?'READY':'01',v>=60?'문턱에 도달했어요. 신호를 보내 보세요.':'슬라이더를 올려 입력을 더해 보세요.',v>=60?'이 단순 모델에서는 입력이 60 이상이면 전기 신호가 발생합니다.':'뉴런은 여러 입력의 영향을 받습니다. 여기서는 하나의 숫자로 단순화해서 비교합니다.');}
 $('#stimulus').addEventListener('input',read);$('#send-signal').addEventListener('click',()=>{reset();if(Number($('#stimulus').value)<60){$('#neuron-caption').innerHTML=caption('WAIT','아직 문턱 아래라서 발화하지 않았어요.','입력을 60 이상으로 올리고 다시 눌러 보세요. 약한 입력도 세포 상태에 영향을 줄 수 있지만, 이 모델에서는 발화를 일으키지 않습니다.');return;}$('#neuron-a').classList.add('node-active');$('#signal-travel').classList.remove('flow-off');$('#neuron-caption').innerHTML=caption('02','뉴런 A 안에서 전기 신호가 이동합니다.','신호가 말단에 도달하면 세포 사이 전달이 이어집니다.');timer=setTimeout(()=>{$('#signal-travel').classList.add('flow-off');$('#transmitters').classList.remove('flow-off');$('#neuron-b').classList.add('node-active');$('#neuron-caption').innerHTML=caption('03','전달물질이 다음 세포에 영향을 줍니다.','B의 색 변화는 입력을 받았다는 뜻입니다. B가 실제로 발화할지는 다른 입력과 현재 상태에도 달려 있습니다.');},reducedMotion.matches?0:1200);});read();cleanup=()=>clearTimeout(timer);
}
function setupGraph(){
 let connected=true,running=false;
 $('#experiment').innerHTML=`<div class="lab-canvas">${svgOpen('S에서 A와 B를 거쳐 M으로 연결되는 가상의 방향 그래프')}
 <g stroke="#b3c3d0" stroke-width="2" fill="none" marker-end="url(#arrow)"><path d="M149 140 L277 140"/><path id="graph-middle" d="M337 140 H465"/><path d="M524 140 H654"/></g>
 <g id="graph-route" class="flow-off"><path id="route-line" d="M149 140 H652" stroke="#cd633f" stroke-width="3" fill="none" class="signal-line"/></g>
 ${[[120,'S','감각 입력'],[308,'A','중간 뉴런'],[495,'B','중간 뉴런'],[682,'M','운동 출력']].map(([x,id,label])=>`<circle class="node-circle" cx="${x}" cy="140" r="29" fill="#fff" stroke="#c2d1dc" stroke-width="2"/><text x="${x}" y="146" text-anchor="middle" class="svg-label">${id}</text><text x="${x}" y="200" text-anchor="middle" class="svg-muted">${label}</text>`).join('')}
 <text x="398" y="108" text-anchor="middle" class="svg-tiny" id="edge-label">A → B 연결 있음</text><text x="380" y="249" text-anchor="middle" class="svg-tiny">예시 그래프 · 실제 초파리의 측정 데이터가 아닙니다</text></svg></div>
 <div class="lab-controls"><button id="trace-route" class="btn primary" aria-pressed="false">▶ 경로 따라가기</button><button id="toggle-edge" class="btn" aria-pressed="true">A → B 연결 끊기</button><span class="helper" id="edge-list">엣지: S→A, A→B, B→M</span></div><div class="lab-caption" id="graph-caption" aria-live="polite"></div>`;
 function show(){const edge=$('#graph-middle');edge.style.opacity=connected?'1':'.2';edge.style.strokeDasharray=connected?'none':'4 5';$('#edge-label').textContent=connected?'A → B 연결 있음':'A → B 연결 없음';$('#toggle-edge').textContent=connected?'A → B 연결 끊기':'A → B 다시 연결';$('#toggle-edge').setAttribute('aria-pressed',String(connected));$('#edge-list').textContent=connected?'엣지: S→A, A→B, B→M':'엣지: S→A, B→M';$('#graph-route').classList.toggle('flow-off',!running);$('#route-line').setAttribute('d',connected?'M149 140 H652':'M149 140 H277');$$('.node-circle').forEach((n,i)=>n.classList.toggle('node-active',running&&(connected||i<2)));$('#trace-route').textContent=running?'Ⅱ 경로 표시 멈추기':'▶ 경로 따라가기';$('#trace-route').setAttribute('aria-pressed',String(running));$('#graph-caption').innerHTML=caption(connected?'PATH':'GAP',connected?'S → A → B → M, 이어지는 경로가 있습니다.':'A와 B 사이가 끊겨 M까지 도달할 경로가 없습니다.',connected?'연결을 끊으면 어떤 노드까지 이어지는지 확인해 보세요. 여기서는 도달 가능한 경로만 표시하며, 실제 신경 활동을 계산하지 않습니다.':'이 예시에는 우회로가 없습니다. 실제 뇌에는 여러 갈래와 되먹임 연결이 있어 훨씬 복잡합니다.');}
 $('#trace-route').addEventListener('click',()=>{running=!running;show();});$('#toggle-edge').addEventListener('click',()=>{connected=!connected;show();});show();
}
function setupLoop(){
 let x=160,target=570,step=0,timer=null;
 $('#experiment').innerHTML=`<div class="lab-canvas">${svgOpen('먹이 방향으로 이동하는 초파리와 관찰 행동 피드백 루프','0 0 760 320')}
 <g fill="#fff" stroke="#d2dee7"><rect x="65" y="21" width="168" height="44" rx="8"/><rect x="296" y="21" width="168" height="44" rx="8"/><rect x="526" y="21" width="168" height="44" rx="8"/></g><g text-anchor="middle" class="svg-label"><text x="149" y="48">① 관찰</text><text x="380" y="48">② 행동 선택</text><text x="610" y="48">③ 몸 이동</text></g><path d="M237 43 H289 M468 43 H519" fill="none" stroke="#a5b5c4" stroke-width="2" marker-end="url(#arrow)"/>
 <path d="M610 67 V86 H148 V69" stroke="#d59b79" stroke-width="1.5" fill="none" stroke-dasharray="4 4" marker-end="url(#arrow)"/>
 <rect x="46" y="110" width="668" height="158" rx="15" fill="#edf4ee" fill-opacity=".65" stroke="#d8e3d9"/>
 <path id="fly-trail" d="M160 190 L160 190" stroke="#a0b7a1" stroke-width="2" stroke-dasharray="4 5"/>
 <g id="food" class="arena-food" transform="translate(570 190)"><circle r="24" fill="#e4edd9"/><circle r="11" fill="#b57843"/><path d="M0 -10 Q0 -24 11 -20" stroke="#6e9257" stroke-width="3" fill="none"/><text x="0" y="44" text-anchor="middle" class="svg-tiny">먹이</text></g>
 <g id="fly-position" class="arena-fly" transform="translate(160 190)"><g id="fly-direction"><path d="M-8 -5 L-24 -19 M-9 0 L-28 0 M-8 5 L-24 19 M4 -5 L14 -19 M4 0 L24 -2 M4 5 L14 19" stroke="#657e85" stroke-width="2" fill="none"/><ellipse cx="-7" cy="0" rx="15" ry="9" fill="#769297"/><ellipse cx="-10" cy="-8" rx="15" ry="7" fill="#f9fcff" fill-opacity=".8" stroke="#a3bdc8" transform="rotate(20)"/><ellipse cx="-10" cy="8" rx="15" ry="7" fill="#f9fcff" fill-opacity=".8" stroke="#a3bdc8" transform="rotate(-20)"/><circle cx="10" r="8" fill="#415d67"/><circle cx="14" cy="-4" r="3" fill="#c87956"/><circle cx="14" cy="4" r="3" fill="#c87956"/></g></g>
 <text x="60" y="296" class="svg-tiny" id="loop-readout">STEP 00 · 먹이까지 410</text><text x="700" y="296" class="svg-tiny" text-anchor="end">단위: 화면 좌표</text></svg></div>
 <div class="lab-controls"><button id="loop-step" class="btn primary">한 번 움직이기 →</button><button id="loop-auto" class="btn">▶ 자동 반복</button><button id="loop-reset" class="btn">처음 위치로</button><label class="range-control" for="food-position">먹이 위치 <input type="range" id="food-position" min="95" max="665" value="570" step="5"><output for="food-position" id="food-value">570</output></label></div><div class="lab-caption" id="loop-caption" aria-live="polite"></div>`;
 function stop(){clearInterval(timer);timer=null;$('#loop-auto').textContent='▶ 자동 반복';}
 function draw(){const d=Math.round(Math.abs(target-x));$('#fly-position').setAttribute('transform',`translate(${x} 190)`);$('#food').setAttribute('transform',`translate(${target} 190)`);$('#fly-trail').setAttribute('d',`M160 190 H${x}`);$('#loop-readout').textContent=`STEP ${String(step).padStart(2,'0')} · 먹이까지 ${d}`;$('#food-value').value=target;$('#loop-step').disabled=d===0;$('#loop-auto').disabled=d===0;$('#loop-caption').innerHTML=caption(d===0?'DONE':'LOOP',d===0?'먹이 위치에 도착했어요.':'지금 관찰한 방향으로 한 걸음 이동합니다.',d===0?'먹이를 다른 곳으로 옮기면 새로운 입력을 바탕으로 다시 움직입니다. 이 행동은 사람이 만든 규칙의 결과이며, 학습한 결과는 아닙니다.':`현재 위치 ${Math.round(x)} → 먹이 위치 ${target}. 차이를 읽고 최대 45만큼 이동한 뒤, 거리를 다시 계산합니다. 이 데모에는 뇌 데이터나 학습이 들어 있지 않습니다.`);}
 function move(){const delta=target-x;$('#fly-direction').setAttribute('transform',delta<0?'rotate(180)':'rotate(0)');x+=Math.sign(delta)*Math.min(45,Math.abs(delta));step++;draw();if(x===target)stop();}
 $('#loop-step').addEventListener('click',()=>{stop();move();});$('#loop-auto').addEventListener('click',()=>{if(timer){stop();return;}$('#loop-auto').textContent='Ⅱ 일시정지';timer=setInterval(move,1000);});$('#loop-reset').addEventListener('click',()=>{stop();x=160;step=0;draw();});$('#food-position').addEventListener('input',()=>{target=Number($('#food-position').value);draw();});draw();cleanup=()=>clearInterval(timer);
}
function setupProjectLesson(){
 $('#experiment').innerHTML=`<div class="lab-controls"><div class="mode-tabs"><button class="btn primary" id="rule-mode" aria-pressed="true">규칙 기반</button><button class="btn" id="learn-mode" aria-pressed="false">강화학습</button></div><span class="helper">방법을 바꿔 차이를 확인하세요</span></div><div class="lab-canvas"><div class="route-table" id="control-method"></div></div><div class="lab-caption" id="method-caption" aria-live="polite"></div>`;
 function show(learn){$('#rule-mode').classList.toggle('primary',!learn);$('#learn-mode').classList.toggle('primary',learn);$('#rule-mode').setAttribute('aria-pressed',String(!learn));$('#learn-mode').setAttribute('aria-pressed',String(learn));$('#control-method').innerHTML=(learn?[['01 / OBSERVE','관찰','현재 상태를 읽어요'],['02 / POLICY','정책으로 선택','경험을 바탕으로 행동해요'],['03 / UPDATE','보상으로 조정','더 나은 정책을 찾아요']]:[['01 / OBSERVE','관찰','현재 상태를 읽어요'],['02 / RULE','정해진 규칙','사람이 작성한 조건을 적용해요'],['03 / ACTION','행동','같은 규칙으로 다음에도 선택해요']]).map(([n,t,d])=>`<div class="route-item"><span>${n}</span><strong>${t}</strong><p>${d}</p></div>`).join('');$('#method-caption').innerHTML=caption(learn?'LEARN':'RULE',learn?'학습에서는 행동을 고르는 정책이 조정됩니다.':'규칙 기반에서는 사람이 제어 방식을 정합니다.',learn?'보상을 얻는 경험으로 정책을 조정하고, 별도의 평가로 개선 여부를 확인합니다. 이 화면은 방법 설명이며 실제 학습을 실행하지 않습니다.':'앞 장의 먹이 추적 데모가 여기에 해당합니다. 먹이에 도달해도 정책이 경험으로 바뀐 것은 아닙니다.');}
 $('#rule-mode').addEventListener('click',()=>show(false));$('#learn-mode').addEventListener('click',()=>show(true));show(false);renderProjectMini();
}
function renderProjectMini(){const el=$('#project-mini');if(!el)return;el.innerHTML=`<article class="explain-card"><span class="mini-label">PROJECT CHECKPOINT</span><h3>이 저장소는 어디까지 왔을까요?</h3>${timeline?`<p>저장된 실행 기록 기준: ${esc(timeline.updated)}. 학습 화면의 완성과 실제 뇌·몸 실험의 진행은 별개입니다.</p><div class="phase-strip">${timeline.phases.filter(p=>[1,2,4,6].includes(p.id)).map(p=>`<span class="status ${statusClass(p.status)}">P${p.id} ${esc(p.title)} · ${statusText(p.status)}</span>`).join('')}</div>`:`<p>${timelineError?'실행 기록을 불러오지 못했습니다. 프로젝트 기록 탭에서 다시 시도해 주세요.':'저장된 실행 기록을 읽고 있습니다…'}</p>`}</article>`;}
function statusClass(s){return ['planned','running','done','failed'].includes(s)?s:'planned';}
function statusText(s){return ({planned:'예정',running:'진행 중으로 기록',done:'완료',failed:'실패'})[s]||esc(s);}
function safeURL(value){try{const u=new URL(value,location.href);return ['http:','https:'].includes(u.protocol)?esc(u.href):'#';}catch{return '#';}}
function renderProject(){
 const openDetails=new Set($$('details[open]', $('#main')).map(d=>d.id).filter(Boolean));
 $('#main').innerHTML=`<div class="breadcrumb"><span>프로젝트 기록 <span>/</span> <b>원본 실행 타임라인</b></span><a href="#learn/5">개념 설명으로 돌아가기 ↗</a></div><section class="chapter-hero"><div class="chapter-tag">PROJECT NOTEBOOK</div><h1>실험은 어디까지 왔을까요?</h1><p class="hero-copy">이전 작업의 명령어, 한글 풀이, 결과를 그대로 확인할 수 있습니다. 학습용 그림과 실제 시뮬레이션 결과는 구분해서 기록합니다.</p></section><div class="project-notice"><p>“진행 중”은 마지막으로 저장된 상태이며, 현재 프로세스가 실행 중이라는 뜻은 아닙니다. 과거 계획의 시간표와 소식은 당시 기록입니다.</p></div><div id="project-data"></div>`;
 const area=$('#project-data');
 if(!timeline){area.innerHTML=`<p>${timelineError?'기록을 불러오지 못했습니다. 서버 연결을 확인하고 다시 시도해 주세요.':'실행 기록을 불러오는 중…'}</p>${timelineError?'<button class="btn" id="retry-timeline">다시 불러오기</button>':''}`;if($('#retry-timeline'))$('#retry-timeline').onclick=loadTimeline;return;}
 area.innerHTML=`<p class="meta">마지막 기록 ${esc(timeline.updated)} · ${timeline.steps.length}개 단계 · ${timelineError?'새로고침 실패: 마지막으로 읽은 기록을 표시합니다.':'5초마다 변경 확인'}</p><div class="phases">${timeline.phases.map(p=>`<article class="phase"><span class="status ${statusClass(p.status)}">${statusText(p.status)}</span><b>P${p.id}. ${esc(p.title)}</b><p>${esc(p.goal)}</p></article>`).join('')}</div>
 <details class="archive-notes" id="archived-notes"><summary>이전 조사 노트 · ${timeline.notes?.length||0}개 (당시 원문)</summary><p class="meta">아래 원문은 보존된 이전 조사 기록입니다. 이번 입문 설명의 근거는 각 학습 장 아래에 별도로 연결했습니다.</p>${(timeline.notes||[]).map((n,i)=>`<details class="archive-note" id="note-${i}"><summary>${esc(n.title)} <span class="meta">${esc(n.date)}</span></summary><div class="body">${esc(n.body)}</div><p>${(n.links||[]).map(l=>`<a href="${safeURL(l.u)}" target="_blank" rel="noopener noreferrer">${esc(l.t)} ↗</a>`).join(' · ')}</p></details>`).join('')}</details>
 <h2>실행 타임라인</h2>${timeline.steps.map(s=>`<article class="timeline-step" id="step-${esc(s.id)}"><div class="meta">${esc(s.time)} · P${esc(s.phase)} · <span class="status ${statusClass(s.status)}">${statusText(s.status)}</span></div><h3>#${esc(s.id)} ${esc(s.title)}</h3>${s.why?`<div class="why">${esc(s.why)}</div>`:''}${s.cmd?`<details id="cmd-${esc(s.id)}"><summary>실행 명령어와 한 줄씩 한글 풀이</summary><pre>${esc(s.cmd)}</pre>${s.cmd_ko?.length?`<table class="ko"><caption>명령어 / 한글 풀이</caption><tbody>${s.cmd_ko.map(r=>`<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td></tr>`).join('')}</tbody></table>`:''}</details>`:''}${s.out?`<details id="out-${esc(s.id)}"><summary>실행 출력 보기</summary><pre>${esc(s.out)}</pre></details>`:''}${(s.media||[]).map(m=>/\.(mp4|webm|mov)$/i.test(m)?`<video src="${safeURL(m)}" controls preload="metadata" playsinline></video>`:`<img src="${safeURL(m)}" alt="단계 ${esc(s.id)} 결과 이미지" loading="lazy">`).join('')}</article>`).join('')}`;
 openDetails.forEach(id=>{const d=document.getElementById(id);if(d instanceof HTMLDetailsElement)d.open=true;});
}
function renderGlossary(){
 $('#main').innerHTML=`<div class="breadcrumb"><span>용어 사전 <span>/</span> <b>익숙한 말로 다시 보기</b></span><span>${terms.length}개 개념</span></div><section class="chapter-hero"><div class="chapter-tag">A LITTLE TRANSLATION</div><h1>이 단어, 무슨 뜻이었죠?</h1><p class="hero-copy">외워 두지 않아도 괜찮습니다. 필요할 때 찾아보고, 관련 그림으로 돌아가세요.</p></section><label for="term-search" class="eyebrow">한글 또는 영어로 찾기</label><input type="search" id="term-search" class="glossary-search" placeholder="예: 단백질, 뉴런, DNA, feedback" autocomplete="off"><p class="meta" id="term-count" aria-live="polite"></p><div class="glossary-grid" id="term-results"></div>${sourceHTML(['rna','protein','neuron','map','vfb','fly','rl'])}`;
 function filter(){const q=$('#term-search').value.trim().toLowerCase();const found=terms.filter(t=>t.join(' ').toLowerCase().includes(q));$('#term-count').textContent=`${found.length}개 개념`;$('#term-results').innerHTML=found.length?found.map(([ko,en,desc,n])=>`<article class="term-card"><h3>${ko}</h3><span class="term-en">${en}</span><p>${desc}</p><a href="#learn/${n}">${String(n).padStart(2,'0')} ${lessons[n-1].short}에서 살펴보기 →</a></article>`).join(''):'<p class="empty-result">일치하는 용어가 없어요. 더 짧은 단어나 한글 이름으로 찾아보세요.</p>';}
 $('#term-search').addEventListener('input',filter);filter();
}
async function loadTimeline(){
 try{const response=await fetch('timeline.json?t='+Date.now(),{cache:'no-store'});if(!response.ok)throw new Error('HTTP '+response.status);const txt=await response.text();const d=JSON.parse(txt);if(!Array.isArray(d.steps)||!Array.isArray(d.phases))throw new Error('Invalid timeline');const changed=txt!==timelineText||timelineError;timelineText=txt;timeline=d;timelineError=false;if(changed){if(view==='project')renderProject();if(view==='learn'&&chapter===5)renderProjectMini();}}
 catch{const changed=!timelineError;timelineError=true;if(changed){if(view==='project')renderProject();if(view==='learn'&&chapter===5)renderProjectMini();}}
}
function route({focus=false}={}){
 cleanup();cleanup=()=>{};
 const hash=location.hash.slice(1),match=hash.match(/^learn\/([1-5])$/);
 if(hash==='project'||/^step-\d+$/.test(hash)||hash==='end')view='project';else if(hash==='experiments'||!hash)view='experiments';else if(hash==='glossary')view='glossary';else{view='learn';chapter=match?Number(match[1]):1;}
 document.querySelector('.layout').classList.toggle('lab-layout',view==='experiments');
 $('#footer-evidence').textContent=view==='experiments'?'실제 시뮬레이션 영상과 설명용 모션을 구분해 표시합니다.':'그림은 학습용 개념 모델입니다.';
 updateNav();if(view==='learn')renderLesson();else if(view==='project')renderProject();else if(view==='experiments')cleanup=window.mountExperiments();else renderGlossary();
 document.title=(view==='learn'?lessons[chapter-1].short:view==='project'?'프로젝트 기록':view==='experiments'?'학습 실험':'용어 사전')+' — Fly Brain Lab';
 if(focus){$('#main').focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}
 if(/^step-\d+$/.test(hash))requestAnimationFrame(()=>document.getElementById(hash)?.scrollIntoView());
}
window.addEventListener('hashchange',()=>route({focus:true}));
route();loadTimeline();setInterval(loadTimeline,5000);
