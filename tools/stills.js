const puppeteer=require('puppeteer-core');const fs=require('fs');
(async()=>{
 const times=(process.argv[2]||'0,5,10,15,20,27,35,40,45,50,53,57,60,64,67').split(',').map(Number);
 const browser=await puppeteer.launch({executablePath:'/usr/local/bin/google-chrome',headless:'new',args:['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader','--disable-gpu-sandbox','--hide-scrollbars','--allow-file-access-from-files']});
 const page=await browser.newPage();
 page.on('console',m=>{if(m.type()==='error')console.log('CONSOLE',m.text())});
 page.on('pageerror',e=>console.log('PAGEERROR',e.message));
 await page.setViewport({width:1080,height:1920,deviceScaleFactor:1});
 await page.goto('http://127.0.0.1:8000/engine/index.html',{waitUntil:'load'});
 await page.waitForFunction('window.READY === true',{timeout:30000});
 fs.mkdirSync('analysis/stills',{recursive:true});
 for(const t of times){
   const t0=Date.now();
   await page.evaluate(t=>window.renderAt(t),t);
   await page.screenshot({path:`analysis/stills/t${String(t).replace('.','_')}.png`,type:'png'});
   console.log('t',t,'ms',Date.now()-t0);
 }
 await browser.close();
})();
