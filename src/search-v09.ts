export type SearchPreset<T> = {id:string; name:string; filter:T};
export function safeLoad<T>(key:string,fallback:T):T {try {const x=localStorage.getItem(key);return x?JSON.parse(x) as T:fallback;}catch{return fallback;}}
export function safeSave<T>(key:string,value:T){try{localStorage.setItem(key,JSON.stringify(value));}catch{/* Local preferences are optional; never affect account data. */}}
export function addPreset<T>(items:SearchPreset<T>[],name:string,filter:T):SearchPreset<T>[] {const trimmed=name.trim().slice(0,40);if(!trimmed)return items;const id=crypto.randomUUID();return [...items,{id,name:trimmed,filter}].slice(-20);}
export function queryTokens(query:string):string[]{return query.toLocaleLowerCase().trim().split(/\s+/u).filter(Boolean)}
