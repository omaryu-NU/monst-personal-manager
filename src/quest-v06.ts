import type { Attribute, Character, OwnedCharacter, Quest, Team, TeamHistory } from './types';
import { fruitProgress } from './owned-v05';

export const GIMMICKS = ['重力バリア','ダメージウォール','地雷','ワープ','減速壁','転送壁','魔法陣','ブロック','ウィンド'] as const;
const alias: Record<string,string[]> = {
 '重力バリア':['アンチ重力バリア','超アンチ重力バリア','AGB','超AGB'],
 'ダメージウォール':['アンチダメージウォール','超アンチダメージウォール','ADW','超ADW'],
 '地雷':['マインスイーパー','超マインスイーパー','マインスイーパーM','マインスイーパーL','飛行','MS'],
 'ワープ':['アンチワープ','超アンチワープ','AW'],
 '減速壁':['アンチ減速壁','超アンチ減速壁'],
 '転送壁':['アンチ転送壁','超アンチ転送壁'],
 '魔法陣':['アンチ魔法陣','魔法陣ブースト'],
 'ブロック':['アンチブロック','AB'],
 'ウィンド':['アンチウィンド','超アンチウィンド']
};
export function parseGimmicks(text: string): string[] {return [...new Set(text.split(/[,、，\s/]+/).map(x=>x.trim()).filter(Boolean))];}
export function characterSupports(character:Character|undefined,gimmick:string):boolean {
 if(!character)return false;
 const abilities=[...character.abilities,...(character.gaugeAbilities??[]),...(character.connectAbilities??[])].map(a=>a.replace(/\s+/g,'').toLowerCase());
 const known=alias[gimmick]??[gimmick];
 return abilities.some(a=>known.some(term=>a.includes(term.replace(/\s+/g,'').toLowerCase())));
}
export function matchedGimmicks(character:Character|undefined,gimmicks:string[]):string[] {return gimmicks.filter(g=>characterSupports(character,g));}
export function searchOwnedForQuest(owned:OwnedCharacter[],catalog:Character[],gimmicks:string[],accountId?:string,allAccounts=false):OwnedCharacter[] {
 const byId=new Map(catalog.map(c=>[c.id,c]));
 return owned.filter(o=>(allAccounts||!accountId||o.accountId===accountId)&&gimmicks.every(g=>characterSupports(byId.get(o.characterId),g)));
}
export function normalizeTeam(team:Team):Team {return {...team,slots:[...((team.slots??[]).slice(0,4)),...Array(Math.max(0,4-(team.slots??[]).length)).fill(null)],favorite:team.favorite??false,history:team.history??[],notes:team.notes??''};}
export function teamSnapshot(t:Team):TeamHistory['snapshot'] {return {name:t.name,quest:t.quest,gimmicks:t.gimmicks,slots:[...t.slots],questId:t.questId,favorite:t.favorite,notes:t.notes};}
export function updateTeamWithHistory(team:Team,patch:Partial<Team>,newId:string,at:string,action='編成編集'):Team {
 const old=normalizeTeam(team);
 const next={...old,...patch,slots:patch.slots?[...patch.slots]:old.slots,updatedAt:at};
 if(JSON.stringify(teamSnapshot(old))===JSON.stringify(teamSnapshot(next))&&old.notes===next.notes)return team;
 const entry:TeamHistory={id:newId,at,action,snapshot:teamSnapshot(old)};
 return {...next,history:[...old.history!,entry].slice(-30)};
}
export function restoreTeam(team:Team,historyId:string,newId:string,at:string):Team {
 const h=team.history?.find(h=>h.id===historyId);if(!h)return team;
 return updateTeamWithHistory(team,h.snapshot,newId,at,'履歴から復元');
}
export function duplicateTeam(team:Team,id:string):Team {return {...normalizeTeam(team),id,name:team.name+'（コピー）',history:[],updatedAt:new Date().toISOString()};}
export function resolveSlot(slot:string|null,owned:OwnedCharacter[],catalog:Character[],accounts: {id:string;name:string}[]) {
 const instance=owned.find(o=>o.id===slot);const character=catalog.find(c=>c.id===instance?.characterId);const account=accounts.find(a=>a.id===instance?.accountId);
 return {instance,character,account,fruit:instance?fruitProgress(instance):null};
}
export function comparison(team:Team,quests:Quest[],owned:OwnedCharacter[],catalog:Character[]) {
 const q=quests.find(q=>q.id===team.questId);
 const gimmicks=q?.gimmicks??parseGimmicks(team.gimmicks);
 return team.slots.map(slot=>{const {instance,character,fruit}=resolveSlot(slot,owned,catalog,[]);
 return {present:!!instance,characterName:character?.name??(slot?'削除・未参照の個体':'未設定'),matched:matchedGimmicks(character,gimmicks),total:gimmicks.length,fruitPercent:fruit?.percent??0};});
}
export function makeQuest(accountId:string,id:string,name:string):Quest {return {id,accountId,name,difficulty:'',attribute:'その他' as Attribute,gimmicks:[],memo:''};}
export function escXml(value:unknown):string {return String(value??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&apos;');}
export function teamSvg(team:Team,quests:Quest[],owned:OwnedCharacter[],catalog:Character[],accounts:{id:string;name:string}[]):string {
 const q=quests.find(q=>q.id===team.questId);
 const slots=team.slots.slice(0,4).map((slot,i)=>{const {instance,character,account,fruit}=resolveSlot(slot,owned,catalog,accounts);
 const y=152+i*104;return `<rect x="32" y="${y}" width="736" height="88" rx="14" fill="#16243d"/><text x="54" y="${y+32}" font-size="23" fill="#a8bce1">SLOT ${i+1}</text><text x="190" y="${y+32}" font-size="27" font-weight="bold" fill="#ffffff">${escXml(character?.name??(slot?'参照先なし':'未設定'))}</text><text x="190" y="${y+64}" font-size="17" fill="#9ac5ff">${escXml(account?.name??'')} ${instance?'・厳選 '+(fruit?.percent??0)+'%':''}</text>`;}).join('');
 return `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="630" viewBox="0 0 800 630"><rect width="800" height="630" fill="#0c1426"/><text x="32" y="54" fill="#ffffff" font-size="34" font-weight="bold">${escXml(team.name)}</text><text x="32" y="94" fill="#a8bce1" font-size="21">${escXml(q?.name??team.quest)}</text><text x="32" y="123" fill="#9ac5ff" font-size="17">${escXml((q?.gimmicks??parseGimmicks(team.gimmicks)).join(' / '))}</text>${slots}<text x="32" y="600" fill="#7d96ba" font-size="15">MONST PERSONAL MANAGER ・ 非公式個人用ツール</text></svg>`;
}
