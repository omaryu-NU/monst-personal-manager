import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const ts=require('typescript');
const src=fs.readFileSync(new URL('../src/quest-v06.ts',import.meta.url),'utf8');
const js=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod={exports:{}};
const dep=(name)=>name==='./owned-v05'?{fruitProgress:()=>({met:1,total:2,percent:50,complete:false})}:require(name);
new Function('module','exports','require',js)(mod,mod.exports,dep);
const q=mod.exports;
const character={id:'c1',name:'騎士',attribute:'火',abilities:['超アンチ重力バリア','マインスイーパーM']};
const owned=[{id:'i1',characterId:'c1',accountId:'main',level:1,luck:1,fruits:[],completed:false,memo:''},{id:'i2',characterId:'c1',accountId:'sub',level:10,luck:1,fruits:[],completed:false,memo:''}];
const team={id:'t1',accountId:'main',name:'旧編成',quest:'クエストA',gimmicks:'重力バリア、地雷',slots:['i1',null,null,null]};
test('known gimmicks match canonical ability text without claiming other mechanics',()=>{
 assert.equal(q.characterSupports(character,'重力バリア'),true);
 assert.equal(q.characterSupports(character,'地雷'),true);
 assert.equal(q.characterSupports(character,'ワープ'),false);
 assert.deepEqual(q.parseGimmicks('地雷、重力バリア,地雷'),['地雷','重力バリア']);
});
test('cross-account query filters owned instance ID rather than character ID',()=>{
 assert.deepEqual(q.searchOwnedForQuest(owned,[character],['地雷'],'main',false).map(o=>o.id),['i1']);
 assert.deepEqual(q.searchOwnedForQuest(owned,[character],['地雷'],'main',true).map(o=>o.id),['i1','i2']);
});
test('legacy team is normalized without dropping slot references',()=>{
 const n=q.normalizeTeam(team);assert.equal(n.slots[0],'i1');assert.equal(n.slots.length,4);assert.deepEqual(n.history,[]);
});
test('edit snapshot, history and restore preserve original instance references',()=>{
 const changed=q.updateTeamWithHistory(team,{name:'改訂',slots:['i2',null,null,null]},'h1','2026-11-10T00:00:00Z');
 assert.equal(changed.history.length,1);assert.equal(changed.slots[0],'i2');
 const restored=q.restoreTeam(changed,'h1','h2','2026-11-10T00:01:00Z');
 assert.equal(restored.name,'旧編成');assert.equal(restored.slots[0],'i1');assert.equal(restored.history.length,2);
});
test('comparison uses stable owned instance ID even when same character is owned twice',()=>{
 const actual=q.comparison(team,[],owned,[character]);assert.equal(actual[0].characterName,'騎士');assert.equal(actual[0].matched.length,2);
});
test('SVG exports escape external text and preserve four slots',()=>{
 const xml=q.teamSvg({...team,name:'<bad & name>'},[],owned,[character],[{id:'main',name:'メイン'}]);
 assert.match(xml,/&lt;bad &amp; name&gt;/);assert.equal((xml.match(/SLOT [1-4]/g)||[]).length,4);
});
test('Firestore rules allow quests section and old backup stays protected',()=>{
 const rules=fs.readFileSync(new URL('../firestore.rules',import.meta.url),'utf8');
 assert.match(rules,/'quests'/);assert.match(rules,/private\/state/);
});
test('old v0.5 state validates with quests defaulting to [] and team IDs unchanged',()=>{
 const source=fs.readFileSync(new URL('../src/persistence.ts',import.meta.url),'utf8');
 const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 new Function('module','exports','require',js)(module,module.exports,(name)=>{
  if(name==='./data')return {initialState:()=>({})};
  if(name==='./owned-v05')return {normalizeOwned:(x)=>x};
  throw Error('unknown dependency: '+name);
 });
 const legacy={schemaVersion:1,catalog:[],accounts:[{id:'main',name:'メイン'}],activeAccountId:'main',owned,teams:[team],todos:[],runs:[],bonds:[],events:[]};
 const result=module.exports.validateState(legacy);
 assert.deepEqual(result.quests,[]);
 assert.equal(result.teams[0].slots[0],'i1');
 assert.equal(result.teams[0].id,'t1');
});
