import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('legacy v1 local key is unchanged and cloud v1 remains read-only',()=>{
 assert.match(read('src/persistence.ts'),/monst-personal-v1/);
 assert.match(read('firestore.rules'),/match \/users\/\{uid\}\/private\/state/);
 assert.match(read('firestore.rules'),/allow create, update, delete: if false/);
});
test('local pending queue and recoverable backups exist',()=>{
 const s=read('src/sync-safety.ts');
 assert.match(s,/readPending/);assert.match(s,/keepSafetyBackup/);assert.match(s,/listSafetyBackups/);
});
test('Firestore transaction revision check and realtime listener present',()=>{
 const s=read('src/sync.ts');assert.match(s,/runTransaction/);assert.match(s,/onSnapshot/);assert.match(s,/ConflictError/);
});
test('retry, offline status, and no uncontrolled automatic overwrite',()=>{
 const s=read('src/App.tsx');assert.match(s,/setRetryCount/);assert.match(s,/window.addEventListener\('online'/);assert.match(s,/keepSafetyBackup/);assert.match(s,/confirm\('現在のローカルデータでクラウドを上書き/);
});
test('Firebase emulator configuration',()=>{
 const c=JSON.parse(read('firebase.json'));assert.equal(c.emulators.firestore.port,8080);
 assert.match(read('src/firebase.ts'),/connectFirestoreEmulator/);
});
