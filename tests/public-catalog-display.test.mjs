import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
const s=readFileSync(new URL('../src/technophere-feed.ts',import.meta.url),'utf8');
test('preserves public abilities and details',()=>{
 assert.match(s,/abilities:safeStringList\(c\.abilities\)/);
 for(const field of ['evolution','type','style','race','friendship','ss','rarity','hp','attack','speed','gaugeAbilities','connectAbilities'])assert.match(s,new RegExp(`['\\"]${field}['\\"]`));
});
test('fetches cache-busted current chunks',()=>{
 assert.match(s,/manifest\.generatedAt/);
 assert.match(s,/\?v=\$\{version\}/);
 assert.match(s,/cache:'no-store'/);
});
test('does not persist user data from public loader',()=>{
 assert.doesNotMatch(s,/setDoc\(|updateDoc\(|localStorage\.setItem\(/);
});
