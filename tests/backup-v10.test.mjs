import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);let ts;try{ts=require('typescript')}catch{ts=require('/opt/nvm/versions/node/v22.16.0/lib/node_modules/typescript')}
const transpile=(file)=>ts.transpileModule(readFileSync(new URL(file,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const own={exports:{}};new Function('module','exports',transpile('../src/integrity-v10.ts'))(own,own.exports);
const src=transpile('../src/backup-v10.ts').replace('require("./persistence")','{validateState:(s)=>{if(!s || s.schemaVersion!==1||!Array.isArray(s.owned))throw Error("invalid");return s;}}').replace('require("./integrity-v10")','globalThis.__integrity');
globalThis.__integrity=own.exports;
const m={exports:{}};new Function('module','exports',src)(m,m.exports);
const f=m.exports;const state={schemaVersion:1,accounts:[{id:'main'}],activeAccountId:'main',catalog:[],owned:[],teams:[],quests:[],todos:[],runs:[],bonds:[],events:[],playLogs:[]};
function storage(){const d=new Map();return {getItem:k=>d.get(k)??null,setItem:(k,v)=>d.set(k,v)}}
test('backup preview counts and audits without changing original',()=>{const before=JSON.stringify(state),p=f.inspectBackup(state);assert.equal(p.counts.owned,0);assert.equal(p.issues.length,0);assert.equal(JSON.stringify(state),before)});
test('backup file wrapper can be parsed and old raw JSON is supported',()=>{assert.equal(f.parseBackupFile(JSON.parse(f.downloadBackupFile(state))).state.schemaVersion,1);assert.equal(f.parseBackupFile(state).counts.accounts,1)});
test('invalid backup rejected before restore',()=>assert.throws(()=>f.parseBackupFile({a:1}),/invalid/));
test('history retains five snapshots and records reasons',()=>{const st=storage();for(let i=0;i<7;i++)f.addBackup(state,'snapshot '+i,st);const entries=f.readBackupHistory(st);assert.equal(entries.length,5);assert.equal(entries[0].reason,'snapshot 6')});
test('failed history write keeps previous backups intact',()=>{const st=storage();f.addBackup(state,'original',st);const broken={getItem:st.getItem,setItem:()=>{throw Error('quota')}};assert.throws(()=>f.addBackup(state,'failed',broken),/quota/);assert.equal(f.readBackupHistory(st)[0].reason,'original')});
