import type { Character } from './types';

type Manifest = {schema:number;generatedAt:string|null;count:number;chunks:{path:string;count:number}[]};
const ATTRS = new Set(['火','水','木','光','闇']);

/** Read-only public master: never writes to Firestore or local user state. */
export async function loadPublicCatalog(signal?:AbortSignal):Promise<{rows:Character[];updatedAt:string|null}> {
 const response=await fetch('/catalog/manifest.json',{signal,cache:'no-cache'});
 if(!response.ok)throw Error(`図鑑マスターを取得できません (${response.status})`);
 const manifest=await response.json() as Manifest;
 if(manifest.schema!==1||!Array.isArray(manifest.chunks)||manifest.chunks.length>100)throw Error('マスターの構造が不正です');
 if(manifest.count===0)return {rows:[],updatedAt:null};
 const chunks=await Promise.all(manifest.chunks.map(async chunk=>{
  if(!/^characters-\d{4}\.json$/.test(chunk.path))throw Error('不正なチャンクパス');
  const r=await fetch('/catalog/'+chunk.path,{signal});if(!r.ok)throw Error('図鑑の一部を取得できません');
  const body=await r.json() as {characters:unknown[]};
  if(!Array.isArray(body.characters)||body.characters.length!==chunk.count)throw Error('図鑑レコード数が一致しません');
  return body.characters;
 }));
 const all=chunks.flat();const ids=new Set<string>();const rows:Character[]=[];
 for(const item of all){
  if(!item||typeof item!=='object')throw Error('図鑑レコードの形式が不正です');
  const c=item as Record<string,unknown>;
  if(typeof c.id!=='string'||!/^[0-9]{1,6}$/.test(c.id)||ids.has(c.id)||typeof c.name!=='string'||!c.name.trim()||!ATTRS.has(String(c.attribute)))throw Error('キャラID・名前・属性の検証に失敗');
  ids.add(c.id);
  rows.push({id:c.id,name:c.name,attribute:c.attribute as Character['attribute'],abilities:[],
   ...(typeof c.image==='string' && c.image.startsWith('https://game.technophere.com/monst/')?{image:c.image}:{}),
   ...(typeof c.source==='string' && c.source.startsWith('https://game.technophere.com/monst/')?{source:c.source}:{})});
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
   abilities:own.abilities.length?own.abilities:common.abilities});
 }
 return [...merged.values()];
}
