import type { Character } from './types';

export type CatalogLicense = { name: string; url?: string; permissionConfirmed: boolean };
export type CatalogPackage = {
  format: 'monst-personal-catalog'; version: 2;
  provenance: { provider: string; retrievedAt: string; sourceUrl?: string; license: CatalogLicense };
  characters: unknown[];
};
export type CatalogPreview = { incoming: Character[]; added: number; updated: number; unchanged: number; source: string; warnings: string[] };
const attrs = new Set(['火','水','木','光','闇','その他']);
const fields = ['id','name','attribute','abilities','type','style','race','image','evolution','friendship','ss','source','rarity','hp','attack','speed','strikeShotTurns','friendshipSub','gaugeAbilities','connectAbilities','illustration','updatedAt'] as const;
const optionalStrings = ['type','style','race','evolution','friendship','ss','source','friendshipSub','illustration','updatedAt'] as const;
function object(value: unknown): Record<string, unknown> { if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('オブジェクト形式が必要です'); return value as Record<string,unknown>; }
function string(value: unknown, name:string, required=false): string | undefined {if(value === undefined || value === null || value === ''){if(required)throw Error(`${name}は必須です`);return undefined;}if(typeof value!=='string' || value.length>2000)throw Error(`${name}は2000文字以内の文字列にしてください`);return value.trim();}
function numbers(value:unknown,name:string):number|undefined {if(value===undefined||value===null)return undefined;if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>1_000_000_000)throw Error(`${name}は0以上の数値にしてください`);return value;}
function strings(value: unknown,name:string):string[] {if(value===undefined||value===null)return [];if(!Array.isArray(value)||value.length>60||!value.every(x=>typeof x==='string'&&x.trim().length>0&&x.length<=160))throw Error(`${name}は文字列の配列にしてください`);return value.map((x:string)=>x.trim());}
function url(value:unknown,name:string):string|undefined {const s=string(value,name);if(s && (!s.startsWith('https://') || s.length>2048))throw Error(`${name}はhttps://で始まるURLにしてください`);return s;}
export function validateCharacter(raw:unknown,index:number):Character {
  let c:Record<string,unknown>;
  try {c=object(raw);const id=string(c.id,'id',true)!;const name=string(c.name,'name',true)!;
    if(!attrs.has(c.attribute as string))throw Error('attributeが不正です');
    if(!Array.isArray(c.abilities))throw Error('abilitiesは配列が必要です');
    const result:Character={id,name,attribute:c.attribute as Character['attribute'],abilities:strings(c.abilities,'abilities')};
    for(const key of optionalStrings){const s=string(c[key],key);if(s)(result as unknown as Record<string,unknown>)[key]=s;}
    for(const key of ['rarity','hp','attack','speed','strikeShotTurns'] as const){const n=numbers(c[key],key);if(n!==undefined)(result as unknown as Record<string,unknown>)[key]=n;}
    for(const key of ['gaugeAbilities','connectAbilities'] as const){const a=strings(c[key],key);if(a.length)(result as unknown as Record<string,unknown>)[key]=a;}
    const image=url(c.image,'image');if(image)result.image=image;
    const illustration=url(c.illustration,'illustration');if(illustration)result.illustration=illustration;
    // Legacy/extension fields are deliberately not copied into the saved master records.
    void fields;
    return result;
  }catch(error){throw Error(`${index+1}件目: ${error instanceof Error?error.message:String(error)}`);}
}
const sortCanonical=(v:unknown):unknown=>Array.isArray(v)?v.map(sortCanonical):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).filter(([,x])=>x!==undefined).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>[k,sortCanonical(x)])):v;
export const equivalentCharacter=(a:Character,b:Character)=>JSON.stringify(sortCanonical(a))===JSON.stringify(sortCanonical(b));
export function readCatalogPackage(raw:unknown,existing:Character[]):CatalogPreview {
 if(Array.isArray(raw))throw Error('配列のみのJSONは出典情報がありません。format/version/provenance/characters形式に変換してください');
 const data=object(raw);
 let rows:unknown[];let source='旧形式JSON（利用条件を別途確認してください）';const warnings:string[]=[];
 if(data.format==='monst-personal-catalog'){
  if(data.version!==2)throw Error('未対応の図鑑形式バージョンです');
  const p=object(data.provenance);const license=object(p.license);
  const provider=string(p.provider,'provenance.provider',true)!;
  const licenseName=string(license.name,'provenance.license.name',true)!;
  if(license.permissionConfirmed!==true)throw Error('データ提供元の利用条件を確認し、permissionConfirmedをtrueにしてください');
  if(!string(p.retrievedAt,'provenance.retrievedAt',true)||Number.isNaN(Date.parse(String(p.retrievedAt))))throw Error('取得日時をISO形式で指定してください');
  if(p.sourceUrl!==undefined)url(p.sourceUrl,'provenance.sourceUrl');
  if(license.url!==undefined)url(license.url,'provenance.license.url');
  source=`${provider} / ${licenseName}`;
  if(!license.url)warnings.push('ライセンスURLは未登録です。利用条件を手元で確認してください');
  rows=data.characters as unknown[];
 }else if(Array.isArray(data.characters)){
  throw Error('旧形式の図鑑JSONです。利用条件を記したv2パッケージに変換してください');
 }else throw Error('図鑑データの形式が不正です');
 if(!Array.isArray(rows)||rows.length===0||rows.length>50000)throw Error('charactersは1～50000件の配列にしてください');
 const ids=new Set<string>();const incoming=rows.map((r,i)=>{const c=validateCharacter(r,i);if(ids.has(c.id))throw Error(`重複したキャラID: ${c.id}`);ids.add(c.id);return c;});
 const previous=new Map(existing.map(c=>[c.id,c]));let added=0,updated=0,unchanged=0;
 for(const c of incoming){const old=previous.get(c.id);if(!old)added++;else if(equivalentCharacter(old,c))unchanged++;else updated++;}
 return {incoming,added,updated,unchanged,source,warnings};
}
export function mergeCatalog(existing:Character[], incoming:Character[]):Character[]{const next=new Map(existing.map(c=>[c.id,c]));for(const c of incoming)next.set(c.id,c);return [...next.values()];}
export type CatalogFilter={term:string;attribute:string;evolution:string;type:string;style:string;race:string;ability:string;ownedOnly:boolean};
export function filterCatalog(rows:Character[],f:CatalogFilter,ownedIds:Set<string>):Character[]{
 const queries=f.term.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
 const abilityQueries=f.ability.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
 return rows.filter(c=>{
  if(f.attribute!=='すべて'&&c.attribute!==f.attribute)return false;
  for(const [key,choice] of [['evolution',f.evolution],['type',f.type],['style',f.style],['race',f.race]] as const){if(choice!=='すべて'&&c[key]!==choice)return false;}
  if(f.ownedOnly&&!ownedIds.has(c.id))return false;
  const hay=[c.id,c.name,c.attribute,c.race,c.type,c.style,c.evolution,c.friendship,c.friendshipSub,c.ss,...c.abilities,...(c.gaugeAbilities??[]),...(c.connectAbilities??[])].join(' ').toLocaleLowerCase();
  const abilityHay=[...c.abilities,...(c.gaugeAbilities??[]),...(c.connectAbilities??[])].join(' ').toLocaleLowerCase();
  return queries.every(q=>hay.includes(q))&&abilityQueries.every(q=>abilityHay.includes(q));
 });
}
