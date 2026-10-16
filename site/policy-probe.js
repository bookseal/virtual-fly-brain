'use strict';
window.mountPolicyProbe=function(host,data){
 if(!data?.models?.length)return;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const link=path=>{try{const u=new URL(path,location.href);return u.origin===location.origin?esc(u.href):'#';}catch{return '#';}};
 const kinds=[{route:'rule',label:'사람이 만든 규칙',color:'#65786a',dash:'4 5'},{route:'ppo',label:'PPO 단독 · 10,240회',color:'#b64a28',dash:''},{route:'bc-ppo',label:'모방 후 PPO · 10,240회',color:'#22788c',dash:'10 4'}];
 host.innerHTML=`<section class="policy-probe" aria-labelledby="policy-probe-title"><span class="chapter-tag">POLICY UNIT TEST · 가정 입력에 대한 모델 출력</span><h3 id="policy-probe-title">먹이를 옮겨 입력하면, 선택도 달라질까?</h3><p>저장된 정책을 함수처럼 검사했습니다. 먹이 방향·거리·속력을 가정해 입력하고, 모델이 내보낸 좌우 신호를 읽습니다. <b>몸을 실제로 움직이거나 성공률을 측정하는 화면은 아닙니다.</b> 아래 조절기는 미리 계산한 ${data.cases.length}가지 입력 표에서 값을 고릅니다.</p><div class="probe-controls"><label>학습 seed<select data-probe-seed><option>11</option><option>29</option></select></label><label>먹이까지 거리<select data-probe-distance><option value="7">7 mm · 멀리</option><option value="3">3 mm</option><option value="1.5">1.5 mm · 도착 문턱 바깥</option></select></label><label>몸의 속력<select data-probe-speed><option value="0">0 mm/s · 정지 가정</option><option value="6">6 mm/s</option><option value="12">12 mm/s</option></select></label><label class="probe-angle">먹이 방향 <output data-probe-angle-value>0° · 정면</output><input data-probe-angle type="range" min="-40" max="40" step="5" value="0" aria-label="가정한 먹이 방향"></label></div><div class="probe-diagrams"><figure><svg viewBox="0 0 360 230" role="img" aria-label="가정한 먹이의 상대 위치"><circle cx="95" cy="110" r="20" fill="#e2d9ce"/><text x="95" y="115" text-anchor="middle">몸</text><path d="M120 110H180l-8 -5m8 5l-8 5" fill="none" stroke="#5b6c60" stroke-width="2"/><text x="135" y="135">정면</text><path data-food-direction fill="none" stroke="#2d7543" stroke-width="2" stroke-dasharray="5 5"/><circle data-probe-food r="8" fill="#2d7543"/><text data-food-label>먹이</text><text x="20" y="214">위치 설명 그림 · 실제 이동 경로 아님</text></svg><figcaption>다른 입력은 고정합니다. 회전 속력 0, 장애물 없음.</figcaption></figure><figure><svg viewBox="0 0 540 260" role="img" aria-label="먹이 방향에 따른 계산된 좌우 신호 차이"><path d="M50 20V220H510M50 120H510" fill="none" stroke="#d0d8d0"/><text x="38" y="26" text-anchor="end">+2</text><text x="38" y="125" text-anchor="end">0</text><text x="38" y="223" text-anchor="end">−2</text><text x="50" y="246">−40°</text><text x="280" y="246" text-anchor="middle">정면</text><text x="510" y="246" text-anchor="end">+40°</text><g data-policy-curves></g><path data-probe-cursor d="M280 20V220" stroke="#9c8c7b" stroke-dasharray="2 4"/><g data-probe-points></g></svg><figcaption>가로: 먹이 방향 · 세로: 오른쪽 신호 − 왼쪽 신호</figcaption></figure></div><div class="probe-readouts" aria-live="polite"></div><p class="probe-boundary">좌우 신호의 차이는 몸 제어기에 전달되는 명령 차이입니다. 실제 회전 각도나 이동 속도로 읽으면 안 됩니다. 도착 문턱은 1.2 mm이고, 여기서는 그 바깥의 입력만 살펴봅니다.</p><details><summary>입력 조건과 원본 계산 보기</summary><p>${esc(data.input_definition)}</p><p>${esc(data.selection_note)}</p><p>${esc(data.limitation)}</p><p><a href="${link(data.record_url)}" target="_blank" rel="noopener">원본 계산 JSON ↗</a> · <a href="${link(data.source_version.path+'/lab/policy_probe.py')}" target="_blank" rel="noopener">실행한 소스 ↗</a></p><p class="meta">계산 ${esc(data.at)} · ${data.cases.length}개 가정 입력 × ${data.models.length}개 체크포인트</p></details></section>`;
 const q=s=>host.querySelector(s),x=a=>50+(a+40)/80*460,y=d=>120-d*50;
 function draw(){
  const seed=Number(q('[data-probe-seed]').value),distance=Number(q('[data-probe-distance]').value),speed=Number(q('[data-probe-speed]').value),angle=Number(q('[data-probe-angle]').value);
  const indices=data.cases.flatMap((c,i)=>c.distance_mm===distance&&c.speed_mm_per_second===speed?[i]:[]);
  const selected=indices.find(i=>data.cases[i].food_angle_degrees===angle);
  if(selected===undefined)return;
  q('[data-probe-angle-value]').value=angle===0?'0° · 정면':`${angle>0?'+':''}${angle}°`;
  q('[data-probe-angle]').setAttribute('aria-valuetext',`${angle}도`);
  const rad=angle*Math.PI/180,length=25+distance*14,px=95+length*Math.cos(rad),py=110-length*Math.sin(rad);
  q('[data-probe-food]').setAttribute('cx',px);q('[data-probe-food]').setAttribute('cy',py);q('[data-food-label]').setAttribute('x',px+12);q('[data-food-label]').setAttribute('y',py+4);q('[data-food-direction]').setAttribute('d',`M95 110L${px} ${py}`);
  q('[data-probe-cursor]').setAttribute('d',`M${x(angle)} 20V220`);
  const lines=[],points=[],cards=[];
  for(const kind of kinds){
   const model=data.models.find(m=>m.seed===seed&&m.route===kind.route&&m.timesteps===10240);
   if(kind.route!=='rule'&&!model)continue;
   const signals=i=>kind.route==='rule'?data.reference_rule_signals[i]:model.values[i].physical_signal;
   const values=signals(selected),difference=values[1]-values[0];
   lines.push(`<polyline points="${indices.map(i=>{const v=signals(i);return `${x(data.cases[i].food_angle_degrees)},${y(v[1]-v[0])}`;}).join(' ')}" fill="none" stroke="${kind.color}" stroke-width="3" stroke-dasharray="${kind.dash}"/>`);
   points.push(`<circle cx="${x(angle)}" cy="${y(difference)}" r="5" fill="${kind.color}" stroke="white" stroke-width="1.5"/>`);
   cards.push(`<article style="border-top-color:${kind.color}"><h4>${kind.label}</h4><dl><div><dt>왼쪽 신호</dt><dd data-signal-left="${kind.route}">${values[0].toFixed(3)}</dd></div><div><dt>오른쪽 신호</dt><dd data-signal-right="${kind.route}">${values[1].toFixed(3)}</dd></div><div><dt>오른쪽 − 왼쪽</dt><dd>${difference.toFixed(3)}</dd></div></dl>${model?`<p class="meta">학습된 평균 선택 · 무작위 흔들기 제외</p>`:'<p class="meta">비교용 수식 · 학습한 모델 아님</p>'}</article>`);
  }
  q('[data-policy-curves]').innerHTML=lines.join('');q('[data-probe-points]').innerHTML=points.join('');q('.probe-readouts').innerHTML=cards.join('');
 }
 host.querySelectorAll('select,input').forEach(control=>control.addEventListener('input',draw));draw();
};
