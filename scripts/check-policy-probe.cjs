const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto((process.env.FLY_UI_BASE||'http://localhost:8765')+'/#experiments?run=20261015-220404',{waitUntil:'domcontentloaded'});
  await page.locator('#policy-probe-title').waitFor();
  const number=async side=>Number(await page.locator(`[data-signal-${side}="ppo"]`).innerText());
  if(Math.abs(await number('left')-.006)>.001)throw Error('Wrong initial policy output');
  await page.locator('[data-probe-distance]').selectOption('1.5');
  if(Math.abs(await number('left')-(-.249))>.001)throw Error('Distance did not change queried input');
  await page.locator('[data-probe-seed]').selectOption('29');
  if(Math.abs(await number('left')-.158)>.001)throw Error('Seed selection mixed models');
  await page.locator('[data-probe-distance]').selectOption('7');await page.locator('[data-probe-speed]').selectOption('12');
  if(Math.abs(await number('left')-.213)>.001)throw Error('Speed did not change queried input');
  const angle=page.locator('[data-probe-angle]');await angle.focus();await angle.press('End');
  if(await angle.inputValue()!=='40')throw Error('Keyboard direction control failed');
  for(const value of ['-40','40']){
   await angle.fill(value);
   const circle=await page.locator('[data-probe-food]').evaluate(e=>({x:+e.getAttribute('cx'),y:+e.getAttribute('cy'),r:+e.getAttribute('r')}));
   if(circle.x-circle.r<0||circle.x+circle.r>360||circle.y-circle.r<0||circle.y+circle.r>230)throw Error('Food diagram clips an extreme direction');
  }
  if(!(await page.locator('.policy-probe').innerText()).includes('실제로 움직이거나 성공률을 측정하는 화면은 아닙니다'))throw Error('Missing hypothetical-input boundary');
  await page.locator('.policy-probe').screenshot({path:'runs/20261015-220404/media/policy-probe-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
  await page.locator('.policy-probe').screenshot({path:'runs/20261015-220404/media/policy-probe-mobile.png'});
  if(errors.length)throw Error(errors.join('\n'));
  console.log('Policy query: exact saved outputs, distance/seed/speed input isolation, keyboard angle, diagram bounds, hypothetical label, mobile PASS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
