import {test,expect} from '@playwright/test';
import {mkdirSync,writeFileSync} from 'node:fs';
test('record atlas load and cell panel performance baseline',async({browser})=>{
 test.setTimeout(90000);
 const results=[];
 for(const viewport of [{width:1280,height:800},{width:390,height:844}]){
  const context=await browser.newContext({viewport});
  try{
   const page=await context.newPage();
   const start=Date.now();
   await page.goto('/');
   await expect(page.getByTestId('map')).toHaveAttribute('data-ready','true',{timeout:20000});
   const mapReady=Date.now()-start;
   await expect(page.getByTestId('feature-count')).not.toContainText('جارٍ تحميل المعالم');
   const dataReady=Date.now()-start;
   const cellStart=Date.now();
   await page.getByRole('button',{name:'التحليل',exact:true}).click();
   await expect(page.getByTestId('cell-count')).toHaveText('2480 خلية');
   const cellPanel=Date.now()-cellStart;
   const resources=await page.evaluate(()=>({resources:performance.getEntriesByType('resource').length,
    transferBytes:performance.getEntriesByType('resource').reduce((s,r)=>s+(r as PerformanceResourceTiming).transferSize,0),
    navigationMs:Math.round(performance.getEntriesByType('navigation')[0]?.duration??0)}));
   results.push({viewport,mapReadyMs:mapReady,dataReadyMs:dataReady,cellPanelMs:cellPanel,...resources});
  }finally{await context.close();}
 }
 mkdirSync('test-results',{recursive:true});
 writeFileSync('test-results/performance-baseline.json',JSON.stringify({environment:'headless Chromium, software WebGL; one fresh context per viewport; DOM readiness, not paint/frame time',results},null,2));
 console.log('BROWSER_BENCHMARK '+JSON.stringify(results));
});
