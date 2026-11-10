import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
let ts;try{ts=require('typescript')}catch{ts=require('/opt/nvm/versions/node/v22.16.0/lib/node_modules/typescript')}
const source=readFileSync(new URL('../src/integrity-v10.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const obj={exports:{}};new Function('module','exports',js)(obj,obj.exports);const {auditState,summary,criticalIssues,snapshotSize}=obj.exports;
const empty=()=>({schemaVersion:1,accounts:[{id:'main',name:'main'}],activeAccountId:'main',catalog:[{id:'c1',name:'test',attribute:'火',abilities:[]}],owned:[{id:'o1',accountId:'main',characterId:'c1',luck:1,level:1}],teams:[{id:'t1',accountId:'main',slots:['o1',null,null,null]}],quests:[],todos:[],runs:[],bonds:[],events:[],playLogs:[]});
test('valid state has no errors and counts correctly',()=>{const s=empty();assert.equal(auditState(s).length,0);assert.equal(summary(s).owned,1);assert.ok(snapshotSize(s)>100)});
test('duplicate IDs detected without mutating source',()=>{const s=empty(),before=JSON.stringify(s);s.owned.push({...s.owned[0]});assert.match(auditState(s).map(i=>i.message).join(' '),/重複/);assert.equal(criticalIssues(s).length,1);assert.notEqual(JSON.stringify(s),before)});
test('dangling team reference is warning (not automatic deletion)',()=>{const s=empty();s.teams[0].slots[0]='removed';const issues=auditState(s);assert.equal(issues[0].level,'warning');assert.equal(s.teams[0].slots[0],'removed')});
test('missing character catalog entry is warning and owned record stays',()=>{const s=empty();s.owned[0].characterId='missing';assert.equal(auditState(s).filter(i=>i.level==='warning').length,1);assert.equal(s.owned.length,1)});
test('cross-reference errors include missing account and invalid active account',()=>{const s=empty();s.activeAccountId='absent';s.owned[0].accountId='absent';assert.equal(criticalIssues(s).length,2)});
test('invalid luck, level and malformed team detected',()=>{const s=empty();s.owned[0].luck=-1;s.owned[0].level=Number.NaN;s.teams[0].slots=[];assert.equal(criticalIssues(s).length,3)});
test('play log stale team and quest references are warnings',()=>{const s=empty();s.playLogs=[{id:'p1',accountId:'main',quest:'q',date:'2026-01-01',result:'勝利',memo:'',teamId:'unknown',questId:'unknown'}];assert.equal(auditState(s).filter(i=>i.level==='warning').length,2)});
