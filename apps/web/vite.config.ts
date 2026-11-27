import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
// MapLibre 6 resolves its module worker relative to import.meta.url at
// runtime. Vite cannot statically discover that computed URL. Emit the
// exact worker beside the bundled entry, from the locked package only.
const workerPath=fileURLToPath(new URL('./node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs',import.meta.url));
const localMapWorker={
 name:'satac-local-maplibre-worker',
 generateBundle(this:import('rollup').PluginContext){
  this.emitFile({type:'asset',fileName:'assets/maplibre-gl-worker.mjs',source:readFileSync(workerPath)});
 }
};
const proxy = {'/api': 'http://127.0.0.1:8000', '/health': 'http://127.0.0.1:8000'};
// Preview-only browser policy; production reverse proxy must apply equivalent headers.
const previewHeaders={
 'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
 'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
 'Permissions-Policy':'camera=(), microphone=(), geolocation=(), payment=()',
 'Cross-Origin-Resource-Policy':'same-origin'
};
export default defineConfig({plugins:[react(),localMapWorker],server:{host:'127.0.0.1',port:5173,strictPort:true,proxy},preview:{host:'127.0.0.1',port:4173,strictPort:true,proxy,headers:previewHeaders}});
