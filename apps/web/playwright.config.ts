import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',workers:1,timeout:45000,use:{baseURL:'http://127.0.0.1:4173',headless:true,launchOptions:{args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']}},
 webServer:[{command:'python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000',cwd:'../..',url:'http://127.0.0.1:8000/health',reuseExistingServer:false,timeout:60000},
 {command:'npm run preview',url:'http://127.0.0.1:4173',reuseExistingServer:false,timeout:60000}]});
