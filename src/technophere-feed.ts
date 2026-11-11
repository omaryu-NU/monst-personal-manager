import type { Character } from './types';

type Manifest = {schema:number;generatedAt:string|null;count:number;chunks:{path:string;count:number}[]};
const ATTRS = new Set(['火','水','木','光','闇']);
const SOURCE_PREFIX = 'https://game.technophere.com/monst/';

function validString(value: unknown): value is string {
 return typeof value === 'string' && value.trim().length > 0 && value.length <= 2000;
}
function validNumber(value: unknown): value is number {
 return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1_000_000_000;
}
function safeStringList(value: unknown): string[] {
 if(!Array.isArray(value) || value.length>60) return [];
 return value.filter((v):v is string=>typeof v==='string'&&v.trim().length>0&&v.length<=160).map(v=>v.trim());
}
/** Public catalog fields are read-only; do not write these to Firestore here. */
export function parsePublicCharacter(c:Record<string,unknown>): Character {
 if(typeof c.id!=='string'||!/^[0-9]{1,6}$/.test(c.id)||!validString(c.name)||!ATTRS.has(String(c.attribute))) {
  throw Error('キャラID・名前・属性の検証に失敗');
 }
 const row:Character = {id:c.id,name:c.name.trim(),attribute:c.attribute as Character['attribute'],abilities:safeStringList(c.abilities)};
 for(const key of ['evolution','type','style','race','friendship','ss','friendshipSub','updatedAt'] as const){
  if(validString(c[key])) row[key]=c[key].trim();
 }
 for(const key of ['rarity','hp','attack','speed','strikeShotTurns'] as const){
  if(validNumber(c[key])) row[key]=c[key];
 }
 for(const key of ['gaugeAbilities','connectAbilities'] as const){
  const list=safeStringList(c[key]); if(list.length) row[key]=list;
 }
 for(const key of ['image','source','illustration'] as const){
  if(validString(c[key]) && c[key].startsWith(SOURCE_PREFIX)) row[key]=c[key];
 }
 return row;
}

/** Fetch new published chunks each time the app loads, not stale browser-cached chunks. */
export async function loadPublicCatalog(signal?:AbortSignal):Promise<{rows:Character[];updatedAt:string|null}> {
 const response=await fetch('/catalog/manifest.json',{signal,cache:'no-store'});
 if(!response.ok)throw Error(`図鑑マスターを取得できません (${response.status})`);
 const manifest=await response.json() as Manifest;
 if(manifest.schema!==1||!Array.isArray(manifest.chunks)||manifest.chunks.length>100||!Number.isInteger(manifest.count)||manifest.count<0)throw Error('マスターの構造が不正です');
 if(manifest.count===0)return {rows:[],updatedAt:manifest.generatedAt};
 const version=typeof manifest.generatedAt==='string' ? encodeURIComponent(manifest.generatedAt) : 'unknown';
 const chunks=await Promise.all(manifest.chunks.map(async chunk=>{
  if(!/^characters-\d{4}\.json$/.test(chunk.path)||!Number.isInteger(chunk.count)||chunk.count<0||chunk.count>200)throw Error('不正なチャンク情報');
  const r=await fetch(`/catalog/${chunk.path}?v=${version}`,{signal,cache:'no-store'});
  if(!r.ok)throw Error(`図鑑の一部を取得できません (${r.status})`);
  const body=await r.json() as {characters:unknown[]};
  if(!Array.isArray(body.characters)||body.characters.length!==chunk.count)throw Error('図鑑レコード数が一致しません');
  return body.characters;
 }));
 const all=chunks.flat();const ids=new Set<string>();const rows:Character[]=[];
 for(const item of all){
  if(!item||typeof item!=='object'||Array.isArray(item))throw Error('図鑑レコードの形式が不正です');
  const row=parsePublicCharacter(item as Record<string,unknown>);
  if(ids.has(row.id))throw Error(`キャラIDの重複: ${row.id}`);
  ids.add(row.id);rows.push(row);
 }
 if(rows.length!==manifest.count)throw Error('マニフェストの件数と一致しません');
 return {rows,updatedAt:manifest.generatedAt};
}

export function overlayCatalog(privateCatalog:Character[],master:Character[]):Character[]{
 const merged=new Map(master.map(c=>[c.id,c]));
 for(const own of privateCatalog){
  const common=merged.get(own.id);
  if(!common)merged.set(own.id,own);
  else merged.set(own.id,{...own,name:common.name,attribute:common.attribute,
   image:common.image??own.image,source:common.source??own.source,
   abilities:common.abilities.length?common.abilities:own.abilities,
   evolution:common.evolution??own.evolution,type:common.type??own.type,
   style:common.style??own.style,race:common.race??own.race,
   rarity:common.rarity??own.rarity,hp:common.hp??own.hp,
   attack:common.attack??own.attack,speed:common.speed??own.speed,
   ss:common.ss??own.ss,friendship:common.friendship??own.friendship,
   gaugeAbilities:common.gaugeAbilities??own.gaugeAbilities,
   connectAbilities:common.connectAbilities??own.connectAbilities});
 }
 return [...merged.values()];
}
