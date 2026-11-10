// Run only with: firebase emulators:exec --only auth,firestore "npm run test:emulator"
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {initializeApp,deleteApp} from 'firebase/app';
import {getAuth,connectAuthEmulator,signInAnonymously} from 'firebase/auth';
import {getFirestore,connectFirestoreEmulator,doc,setDoc,getDoc,runTransaction} from 'firebase/firestore';

const projectId=process.env.GCLOUD_PROJECT||'demo-monst-personal-v03';
const makeClient=async(name)=>{
 const app=initializeApp({apiKey:'fake',authDomain:'localhost',projectId,appId:'1:1:web:'+name},name);
 const auth=getAuth(app);connectAuthEmulator(auth,'http://127.0.0.1:9099',{disableWarnings:true});
 const db=getFirestore(app);connectFirestoreEmulator(db,'127.0.0.1',8080);
 const credential=await signInAnonymously(auth);
 return {app,db,uid:credential.user.uid};
};
const payload={value:[],revision:1,updatedAt:new Date()};

test('owners can write only their own section; strangers cannot read or overwrite',async()=>{
 const a=await makeClient('a'+Date.now());const b=await makeClient('b'+Date.now());
 try{
  const own=doc(a.db,'users',a.uid,'data','owned');
  await setDoc(own,payload);
  assert.equal((await getDoc(own)).data()?.revision,1);
  await assert.rejects(getDoc(doc(b.db,'users',a.uid,'data','owned')));
  await assert.rejects(setDoc(doc(b.db,'users',a.uid,'data','owned'),payload));
  await assert.rejects(setDoc(doc(a.db,'users',a.uid,'private','state'),{payload:{}}));
  await assert.rejects(setDoc(doc(a.db,'users',a.uid,'data','unknown'),payload));
  await assert.rejects(setDoc(own,{...payload,revision:5}));
 }finally{await deleteApp(a.app);await deleteApp(b.app);}
});

test('transaction detects concurrent revisions instead of replacing data',async()=>{
 const a=await makeClient('c'+Date.now());
 try{
  const ref=doc(a.db,'users',a.uid,'data','teams');
  await setDoc(ref,payload);
  const expected=1;
  await runTransaction(a.db,async tx=>{const s=await tx.get(ref);tx.set(ref,{...payload,revision:s.data().revision+1});});
  await assert.rejects(runTransaction(a.db,async tx=>{
   const s=await tx.get(ref);
   if(s.data().revision!==expected)throw Error('conflict');
   tx.set(ref,{...payload,revision:expected+1});
  }),/conflict/);
  assert.equal((await getDoc(ref)).data().revision,2);
 }finally{await deleteApp(a.app);}
});


test('v0.6 quest section permits owner writes, rejects other users and nonconsecutive revision',async()=>{
 const a=await makeClient('questA'+Date.now());const b=await makeClient('questB'+Date.now());
 try{
  const ref=doc(a.db,'users',a.uid,'data','quests');
  const quest={id:'q1',accountId:'main',name:'テスト',attribute:'火',difficulty:'',gimmicks:['重力バリア'],memo:''};
  await setDoc(ref,{value:[quest],revision:1,updatedAt:new Date()});
  assert.equal((await getDoc(ref)).data().value[0].id,'q1');
  await assert.rejects(getDoc(doc(b.db,'users',a.uid,'data','quests')));
  await assert.rejects(setDoc(doc(b.db,'users',a.uid,'data','quests'),{value:[],revision:2,updatedAt:new Date()}));
  await assert.rejects(setDoc(ref,{value:[],revision:3,updatedAt:new Date()}));
 }finally{await deleteApp(a.app);await deleteApp(b.app);}
});


test('v0.7 playLogs owner writes allowed, cross-user blocked, revisions sequential',async()=>{
 const a=await makeClient('playA'+Date.now());const b=await makeClient('playB'+Date.now());
 try{
  const ref=doc(a.db,'users',a.uid,'data','playLogs');
  const row={id:'log-1',accountId:'main',quest:'テスト',date:'2026-11-10',result:'勝利',memo:''};
  await setDoc(ref,{value:[row],revision:1,updatedAt:new Date()});
  assert.equal((await getDoc(ref)).data()?.value[0].result,'勝利');
  await assert.rejects(getDoc(doc(b.db,'users',a.uid,'data','playLogs')));
  await assert.rejects(setDoc(doc(b.db,'users',a.uid,'data','playLogs'),{value:[],revision:2,updatedAt:new Date()}));
  await assert.rejects(setDoc(ref,{value:[],revision:3,updatedAt:new Date()}));
  await setDoc(ref,{value:[],revision:2,updatedAt:new Date()});
 }finally{await deleteApp(a.app);await deleteApp(b.app);}
});

test('v1.0: section cannot be deleted, legacy document remains read-only, unexpected fields blocked',async()=>{
 const a=await makeClient('v10'+Date.now());
 try {
  const ref=doc(a.db,'users',a.uid,'data','owned');
  await setDoc(ref,{value:[],revision:1,updatedAt:new Date()});
  await assert.rejects(setDoc(ref,{value:[],revision:2,updatedAt:new Date(),admin:true}));
  await assert.rejects(setDoc(doc(a.db,'users',a.uid,'private','state'),{payload:{},schemaVersion:1}));
  await assert.rejects(setDoc(doc(a.db,'users',a.uid,'data','owned'),{value:[],revision:1,updatedAt:new Date()}));
  assert.equal((await getDoc(ref)).data().revision,1);
 }finally{await deleteApp(a.app)}
});
