import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
const require=createRequire(import.meta.url);
const ts=require('typescript');
const source=fs.readFileSync(new URL('../src/owned-v05.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod={exports:{}};new Function('module','exports','require',js)(mod,mod.exports,require);
const { normalizeOwned, fruitProgress, updateFruitSlot, bulkUpdate, appendHistory, legacyFruit }=mod.exports;
const sample=()=>({id:'instance-1',characterId:'char-1',accountId:'main',luck:1,level:1,memo:'',fruits:['熱き友撃 特L'],targetFruits:['熱き友撃 特L'],completed:false});
test('v0.4 legacy strings migrate without overwriting ID and fruit strings',()=>{
 const old=sample(),fresh=normalizeOwned(old);assert.equal(fresh.id,old.id);assert.deepEqual(fresh.fruits,old.fruits);assert.equal(fresh.fruitSlots[0].name,'熱き友撃');assert.equal(fresh.fruitSlots[0].grade,'特L');assert.equal(fresh.fruitTargets[0].grade,'特L');assert.equal(fruitProgress(fresh).complete,true);assert.equal(old.fruitSlots,undefined);
});
test('grade and duplicate multiplicity are considered during auto completion',()=>{
 const o={...sample(),fruits:[],targetFruits:[],fruitSlots:[{name:'同族加撃',grade:'特級L'}],fruitTargets:[{name:'同族加撃',grade:'特級L'},{name:'同族加撃',grade:'特級L'}]};
 assert.deepEqual(fruitProgress(o),{met:1,total:2,percent:50,complete:false});
 const next=updateFruitSlot(o,'fruitSlots',1,{name:'同族加撃',grade:'特級L'});
 assert.equal(fruitProgress(next).complete,true);assert.equal(next.fruits.length,2);
});
test('bulk edits affect only selected instances; character and team references remain',()=>{
 const a=sample(),b={...sample(),id:'instance-2'};const state={schemaVersion:1,owned:[a,b],teams:[{id:'t1',slots:[a.id,b.id,null,null]}]};let counter=0;
 const updated=bulkUpdate(state,[a.id],{favorite:true,tag:'周回用',trainingStatus:'育成中'},()=>String(++counter),'2026-11-10T00:00:00Z');
 assert.equal(updated.owned[0].favorite,true);assert.deepEqual(updated.owned[0].tags,['周回用']);assert.equal(updated.owned[1].favorite,undefined);assert.deepEqual(updated.teams,state.teams);assert.equal(updated.owned[0].history.length,1);
});
test('history is bounded; unknown legacy fruit labels are preserved',()=>{
 assert.equal(legacyFruit('独自名称').name,'独自名称');let o=sample();for(let i=0;i<50;i++)o=appendHistory(o,'test','detail',String(i),'2026-11-10T00:00:00Z');
 assert.equal(o.history.length,40);assert.equal(o.history[0].id,'10');
});
