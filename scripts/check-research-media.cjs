const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
  const base=process.env.FLY_UI_BASE||'http://localhost:8765',run='20261015-220404';
  const response=await page.request.get(`${base}/artifacts/${run}/manifest.json`);if(!response.ok())throw Error('Manifest unavailable');
  const manifest=await response.json(),entry=manifest.journal.entries.find(e=>e.title==='조사 범위를 바로잡고 새 API를 별도로 실행');
  if(!entry)throw Error('Compatibility research entry missing');
  if(manifest.publication&&('quota' in manifest||'model_allowance' in manifest))throw Error('Private allowance leaked into public snapshot');
  await page.goto(`${base}/#experiments?run=${run}&decision=${entry.id}`,{waitUntil:'domcontentloaded'});
  await page.locator('.decision-body h3').waitFor();
  if(await page.locator('.decision-body h3').innerText()!==entry.question)throw Error('Shared decision did not open');
  await page.reload({waitUntil:'domcontentloaded'});await page.locator('.decision-film video').waitFor();
  for(const [selector,seconds] of [['.decision-film video',24],['.compatibility-results video',2]]){
   const video=page.locator(selector).first();await video.scrollIntoViewIfNeeded();
   await video.evaluate(v=>{v.muted=true;return v.play();});
   await page.waitForFunction(selector=>document.querySelector(selector).currentTime>.2,selector);
   const duration=await video.evaluate(v=>{v.pause();return v.duration;});if(Math.abs(duration-seconds)>.05)throw Error(`${selector} has unexpected duration ${duration}`);
  }
  const modern=manifest.compatibility.records.find(r=>r.flavor==='modern');
  const lock=await page.request.get(`${base}/${modern.requirements}`);if(!lock.ok()||!(await lock.text()).includes('flygym==2.1.0'))throw Error('Dependency lock missing');
  await page.locator('.compatibility-story').screenshot({path:'runs/20261015-220404/media/compatibility-public-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
  if(errors.length)throw Error(errors.join('\n'));
  console.log('Research media: direct decision/reload, 24s recap + 2s actual video decoded/played, dependency link, privacy, mobile PASS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
