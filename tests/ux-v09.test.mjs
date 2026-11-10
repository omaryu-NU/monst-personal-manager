import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
let ts;try{ts=require('typescript')}catch{ts=require('/opt/nvm/versions/node/v22.16.0/lib/node_modules/typescript')}
const root=path.resolve(import.meta.dirname,'..');
const get=f=>fs.readFileSync(path.join(root,f),'utf8');
const pure=ts.transpileModule(get('src/search-v09.ts'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const module={exports:{}};new Function('module','exports',pure)(module,module.exports);
test('presets keep multiple independent entries and reject blank names',()=>{const {addPreset}=module.exports;const a=addPreset([], '  test ',{term:'fire'});assert.equal(a.length,1);assert.equal(a[0].name,'test');assert.equal(addPreset(a,'   ',{}).length,1)});
test('query tokenizer handles Japanese whitespace',()=>{assert.deepEqual(module.exports.queryTokens('  火  アンチワープ  '),['火','アンチワープ'])});
test('PWA never intercepts non-GET or third-party requests',()=>{const code=get('public/sw.js');assert.match(code,/req.method!==['"]GET['"]/);assert.match(code,/url.origin!==self.location.origin/);assert.doesNotMatch(code,/firebase\.googleapis\.com/)});
test('PWA does not force install-time activation',()=>{const code=get('public/sw.js');const install=code.slice(code.indexOf("addEventListener('install'"),code.indexOf("addEventListener('activate'"));assert.doesNotMatch(install,/skipWaiting/)});
test('data schema and Firebase sync remain present',()=>{assert.match(get('src/App.tsx'),/saveSections/);assert.match(get('src/App.tsx'),/loadLocal/);assert.match(get('src/App.tsx'),/PwaStatus/)});
test('mobile navigation presents five items and more menu',()=>{const code=get('src/App.tsx');assert.match(code,/v09-more-menu/);assert.match(code,/aria-expanded={mobileMore}/)});
test('formation controls swap IDs without changing references',()=>{const code=get('src/QuestManager.tsx');assert.match(code,/\[slots\[i-1\],slots\[i\]\]/);assert.match(code,/changeTeam\(t.id,{slots}/)});
