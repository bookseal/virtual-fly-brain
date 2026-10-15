'use strict';
// Replays recorded 50 ms positions. No physics or learning runs in this viewer.
window.createTrajectoryExplorer=function(host,manifest){
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const evaluations=manifest.evaluations||[],groups=[];
 const latest=predicate=>evaluations.filter(predicate).at(-1);
 for(const seed of [11,29]){
  const find=policy=>latest(e=>e.trial===`3d-near-${policy}-seed${seed}`&&e.policy===policy&&e.timesteps===10240&&!e.selection_holdout);
  const a=find('ppo'),b=find('bc-ppo');
  if(a&&b)groups.push({id:`near-${seed}`,label:`가까운 먹이 · 학습 seed ${seed}`,a,b,names:['PPO 단독','모방 후 PPO']});
 }
 const wide=evaluations.filter(e=>e.trial==='3d-wide-generalization-seed11');
 const rule=wide.find(e=>e.policy==='rule'),transfer=wide.find(e=>e.policy!=='rule');
 if(rule&&transfer)groups.push({id:'wide',label:'모든 방향의 먹이 · 별도 진단',a:rule,b:transfer,names:['사람이 만든 규칙','모방 후 PPO']});
 if(!groups.length){host.hidden=true;return {destroy(){}};}
 const safeURL=path=>{const u=new URL(path,location.href);if(!['http:','https:'].includes(u.protocol))throw Error('지원하지 않는 자료 주소입니다.');return u.href;};
 let disposed=false,request=0,controller=null,frame=0,playing=false,t=0,maxTime=0,pairs=[],group=groups[0],pair=null;
 const cache=new Map();
 host.innerHTML=`<section class="trajectory-explorer" aria-labelledby="trajectory-title"><span class="chapter-tag">MEASURED PATHS · 직접 살펴보기</span><h3 id="trajectory-title">같은 먹이, 다른 선택</h3><p>실제로 측정한 위치를 0.05초 단위로 되짚습니다. 초파리 그림을 새로 시뮬레이션하는 화면이 아닙니다. 두 경로의 시간과 지도 축척은 같습니다.</p><div class="trajectory-selectors"><label>비교 실험<select data-path-group>${groups.map(g=>`<option value="${g.id}">${esc(g.label)}</option>`).join('')}</select></label><button class="btn" data-path-load>측정 경로 불러오기</button><label hidden data-seed-label>같은 시작 조건<select data-path-seed></select></label></div><p data-path-status role="status">원본 평가 자료를 불러오면 20개 시작 조건을 하나씩 비교할 수 있습니다.</p><div data-path-content hidden><p class="path-paired-summary"></p><div class="path-stage"><svg viewBox="0 0 680 460" role="img" aria-label="두 정책의 실제 이동 경로"><g data-path-grid></g><g data-path-goal></g><g data-path-lines></g><g data-path-dots></g></svg><div class="path-results"></div></div><div class="path-controls"><button class="btn" data-path-play aria-pressed="false">재생</button><label>시뮬레이션 시각 <output data-path-time>0.00초</output><input data-path-time-slider type="range" min="0" max="8" step="0.05" value="0" aria-label="측정 경로의 시뮬레이션 시각"></label></div><p class="meta">경로 점은 저장된 측정값입니다. 에피소드가 끝난 정책은 마지막 위치에 남습니다. 이 비교에서는 모델을 업데이트하지 않습니다.</p></div></section>`;
 const el=q=>host.querySelector(q),status=el('[data-path-status]'),content=el('[data-path-content]'),slider=el('[data-path-time-slider]'),play=el('[data-path-play]');
 function pause(){playing=false;cancelAnimationFrame(frame);play.textContent='재생';play.setAttribute('aria-pressed','false');}
 function selected(){return groups.find(g=>g.id===el('[data-path-group]').value)||groups[0];}
 async function fetchRecord(ref,signal){
  if(cache.has(ref))return cache.get(ref);
  const response=await fetch(safeURL(ref),{signal});if(!response.ok)throw Error(`원본 자료를 읽지 못했습니다 (${response.status}).`);
  const value=await response.json();if(!Array.isArray(value.episodes_raw))throw Error('측정 경로가 없는 기록입니다.');cache.set(ref,value);return value;
 }
 async function load(){
  const token=++request;controller?.abort();controller=new AbortController();pause();group=selected();content.hidden=true;el('[data-seed-label]').hidden=true;status.textContent='원본 평가 두 개를 읽고 같은 seed와 먹이 위치인지 확인하고 있습니다.';
  try{
   const [a,b]=await Promise.all([fetchRecord(group.a.record_url,controller.signal),fetchRecord(group.b.record_url,controller.signal)]);
   if(disposed||token!==request)return;
   const right=new Map(b.episodes_raw.map(r=>[r.seed,r]));
   pairs=a.episodes_raw.map(left=>[left,right.get(left.seed)]).filter(([left,right])=>right&&Array.isArray(left.path)&&left.path.length&&Array.isArray(right.path)&&right.path.length&&left.target.every((v,i)=>Math.abs(v-right.target[i])<1e-6));
   if(!pairs.length)throw Error('같은 시작 조건으로 짝지을 수 있는 측정 경로가 없습니다.');
   let both=0,onlyA=0,onlyB=0,neither=0;for(const [a,b] of pairs){if(a.success&&b.success)both++;else if(a.success)onlyA++;else if(b.success)onlyB++;else neither++;}
   el('.path-paired-summary').textContent=`같은 위치 ${pairs.length}곳: 둘 다 도착 ${both} · ${group.names[0]}만 ${onlyA} · ${group.names[1]}만 ${onlyB} · 둘 다 실패 ${neither}`;
   el('[data-path-seed]').innerHTML=pairs.map(([a,b])=>`<option value="${a.seed}">seed ${a.seed} · ${a.success?'도착':'실패'} / ${b.success?'도착':'실패'}</option>`).join('');
   el('[data-seed-label]').hidden=false;content.hidden=false;status.textContent=`측정 시각: ${a.evaluated_at} / ${b.evaluated_at}. 지도는 두 정책의 동일한 위치만 짝지었습니다.`;
   choose();
  }catch(error){if(error.name!=='AbortError'&&!disposed&&token===request)status.textContent=error.message+' “측정 경로 불러오기”로 다시 시도할 수 있습니다.';}
 }
 let project=null;
 function choose(){
  pause();pair=pairs.find(([a])=>String(a.seed)===el('[data-path-seed]').value)||pairs[0];t=0;
  const points=pair.flatMap(r=>[...r.path,r.target]),extent=Math.max(4,...points.flat().map(Math.abs))+2;
  project=p=>[340+p[0]*190/extent,230-p[1]*190/extent];
  const point=p=>project(p).map(v=>v.toFixed(2)).join(',');
  el('[data-path-grid]').innerHTML=`<path d="M40 230H640M340 30V430" stroke="#c9d1ce" stroke-dasharray="4 5"/><text x="350" y="448">x (mm)</text><text x="18" y="35">y (mm)</text><text x="350" y="248">시작</text><circle cx="340" cy="230" r="4" fill="#35433e"/><path d="M150 225V235M530 225V235M335 40H345M335 420H345" stroke="#798d80"/><text x="150" y="253" text-anchor="middle">−${extent.toFixed(1)}</text><text x="530" y="253" text-anchor="middle">${extent.toFixed(1)}</text>`;
  const [gx,gy]=project(pair[0].target),radius=1.2*190/extent;
  el('[data-path-goal]').innerHTML=`<circle cx="${gx}" cy="${gy}" r="${radius}" fill="#71ae7850" stroke="#2d7543" stroke-dasharray="3 3"/><circle cx="${gx}" cy="${gy}" r="5" fill="#2d7543"/><text x="${gx+9}" y="${gy-9}">먹이</text>`;
  el('[data-path-lines]').innerHTML=pair.map((r,i)=>`<polyline data-recorded-line="${i}" points="${r.path.map(point).join(' ')}" fill="none" stroke="${i?'#22788c':'#b94d28'}" stroke-width="3" ${i?'stroke-dasharray="7 4"':''} opacity="0.65"/>`).join('');
  el('[data-path-dots]').innerHTML=pair.map((r,i)=>`<circle data-path-dot="${i}" r="${i?5:9}" fill="${i?'#22788c':'white'}" stroke="${i?'white':'#b94d28'}" stroke-width="2"/>`).join('');
  maxTime=Math.max(...pair.map(r=>(r.path.length-1)*.05));slider.max=maxTime;
  el('.path-results').innerHTML=pair.map((r,i)=>`<article class="path-result path-result-${i}"><h4>${esc(group.names[i])}</h4><span class="meta">${i?'점선 · 작은 원':'실선 · 테두리 원'}</span><b>${r.success?'먹이에 도착':'도착하지 못함'}</b><p><span data-distance="${i}"></span><br>에피소드 ${(r.steps*.05).toFixed(2)}초 · 보상 합계 ${r.reward.toFixed(2)}</p><p class="meta">학습 행동 ${Number((i?group.b:group.a).timesteps).toLocaleString('ko-KR')}회${(i?group.b:group.a).policy==='rule'?' · 학습하지 않은 규칙':''}</p><a href="${esc(safeURL((i?group.b:group.a).record_url))}" target="_blank" rel="noopener">이 경로의 원본 ↗</a>${r.seed===(i?group.b:group.a).video_seed&&(i?group.b:group.a).video?`<a href="${esc(safeURL((i?group.b:group.a).video))}" target="_blank" rel="noopener">이 seed의 실제 영상 ↗</a>`:''}</article>`).join('');
  draw();
 }
 function draw(){
  slider.value=t;el('[data-path-time]').value=`${t.toFixed(2)}초`;slider.setAttribute('aria-valuetext',`${t.toFixed(2)}초`);
  pair.forEach((r,i)=>{const n=Math.min(r.path.length-1,Math.floor((t+1e-8)/.05)),p=r.path[n],[x,y]=project(p);const dot=el(`[data-path-dot="${i}"]`);dot.setAttribute('cx',x);dot.setAttribute('cy',y);el(`[data-distance="${i}"]`).textContent=`이 시각 먹이까지 ${Math.hypot(p[0]-r.target[0],p[1]-r.target[1]).toFixed(2)} mm${n===r.path.length-1?' · 기록 종료':''}`;});
 }
 el('[data-path-load]').onclick=load;
 el('[data-path-group]').onchange=()=>{request++;controller?.abort();pause();content.hidden=true;el('[data-seed-label]').hidden=true;status.textContent='선택한 실험의 측정 경로를 불러오세요.';};
 el('[data-path-seed]').onchange=choose;
 slider.oninput=()=>{pause();t=Number(slider.value);draw();};
 play.onclick=()=>{
  if(playing){pause();return;}if(t>=maxTime)t=0;playing=true;play.textContent='일시 정지';play.setAttribute('aria-pressed','true');const origin=performance.now()-t*1000;
  function tick(now){if(!playing||disposed)return;t=Math.min(maxTime,(now-origin)/1000);draw();if(t>=maxTime)pause();else frame=requestAnimationFrame(tick);}frame=requestAnimationFrame(tick);
 };
 const hidden=()=>{if(document.hidden)pause();};document.addEventListener('visibilitychange',hidden);
 return {destroy(){disposed=true;controller?.abort();pause();document.removeEventListener('visibilitychange',hidden);}};
};
