import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const ts=require('typescript');
const source=fs.readFileSync(new URL('../src/catalog-v04.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod={exports:{}};
new Function('module','exports','require',js)(mod,mod.exports,require);
const {readCatalogPackage,mergeCatalog,filterCatalog,validateCharacter}=mod.exports;
const base={id:'100',name:'例キャラ',attribute:'火',abilities:['アンチワープ'],evolution:'獣神化',type:'貫通'};
function pack(characters){return {format:'monst-personal-catalog',version:2,provenance:{provider:'検証用自作データ',retrievedAt:'2026-11-10T00:00:00Z',license:{name:'自作',permissionConfirmed:true}},characters};}
test('v0.3 schema fields are preserved and new optional stats accepted',()=>{
 const item=validateCharacter({...base,hp:25000,attack:29000,rarity:6,gaugeAbilities:['アンチ減速壁']},0);
 assert.equal(item.hp,25000);assert.equal(item.rarity,6);assert.deepEqual(item.gaugeAbilities,['アンチ減速壁']);
});
test('duplicate IDs and invalid schema are rejected before changes',()=>{
 assert.throws(()=>readCatalogPackage(pack([base,base]),[]),/重複/);
 assert.throws(()=>readCatalogPackage(pack([{...base,attribute:'虹'}]),[]),/attribute/);
 assert.throws(()=>readCatalogPackage(pack([{...base,image:'http:\/\/bad'}]),[]),/https/);
});
test('unknown rights and unversioned sources are not imported',()=>{
 assert.throws(()=>readCatalogPackage(pack([base]).characters,[]),/出典/);
 const noPermission=pack([base]);noPermission.provenance.license.permissionConfirmed=false;
 assert.throws(()=>readCatalogPackage(noPermission,[]),/利用条件/);
});
test('added updated and unchanged records counted without deleting old ID',()=>{
 const existing=[base,{...base,id:'200',name:'保護対象'}];
 const incoming=[{...base,name:'更新後'}, {id:'300',name:'追加',attribute:'水',abilities:[]}];
 const preview=readCatalogPackage(pack(incoming),existing);
 assert.deepEqual([preview.added,preview.updated,preview.unchanged],[1,1,0]);
 const result=mergeCatalog(existing,preview.incoming);
 assert.equal(result.length,3);assert.equal(result.find(c=>c.id==='200').name,'保護対象');
 assert.equal(result.find(c=>c.id==='100').name,'更新後');
});
test('AND filters, evolution and owned-only combination',()=>{
 const entries=[base,{id:'200',name:'例キャラ改',attribute:'水',abilities:['アンチワープ','マインスイーパー'],evolution:'獣神化・改',type:'反射'}];
 const f={term:'例キャラ',attribute:'すべて',evolution:'すべて',type:'すべて',style:'すべて',race:'すべて',ability:'アンチワープ マインスイーパー',ownedOnly:false};
 assert.deepEqual(filterCatalog(entries,f,new Set()).map(c=>c.id),['200']);
 assert.deepEqual(filterCatalog(entries,{...f,ownedOnly:true},new Set(['100'])),[]);
 assert.deepEqual(filterCatalog(entries,{...f,ownedOnly:true},new Set(['200'])).map(c=>c.id),['200']);
});
