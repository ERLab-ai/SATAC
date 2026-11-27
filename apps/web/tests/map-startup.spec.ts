import {test,expect} from '@playwright/test';
test('map startup diagnostic and mandatory readiness',async({page})=>{
 const events:string[]=[];
 page.on('console',m=>{if(m.type()==='error'||m.type()==='warning')events.push(m.type()+': '+m.text().slice(0,1800));});
 page.on('pageerror',e=>events.push('pageerror: '+e.message));
 page.on('requestfailed',r=>events.push('request failed: '+new URL(r.url()).pathname+' '+r.failure()?.errorText));
 page.on('response',r=>{if(r.status()>=400)events.push('HTTP '+r.status()+': '+new URL(r.url()).pathname);});
 await page.addInitScript(()=>document.addEventListener('securitypolicyviolation',e=>console.error('CSP violation: '+e.violatedDirective+' '+e.blockedURI)));
 try{
 await page.goto('/');
 await expect(page.getByTestId('map')).toHaveAttribute('data-ready','true',{timeout:20000});
 await expect(page.getByTestId('map')).toHaveAttribute('data-gazetteer-glyphs','ready',{timeout:10000});
 }finally{
 console.log('MAP_STARTUP_DIAGNOSTICS '+JSON.stringify(events.slice(0,40)));
 console.log('WEBGL_CAPABILITIES '+JSON.stringify(await page.evaluate(()=>{const c=document.createElement('canvas');const gl=c.getContext('webgl2');return {webgl2:!!gl,webgl:!!document.createElement('canvas').getContext('webgl'),offscreenCanvas:typeof OffscreenCanvas,worker:typeof Worker};})));
 }
});
