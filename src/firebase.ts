import { initializeApp, getApps } from 'firebase/app';
import { getAuth, connectAuthEmulator, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged, type User } from 'firebase/auth';
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore';
const env = import.meta.env;
export const firebaseEnabled = Boolean(env.VITE_FIREBASE_API_KEY && env.VITE_FIREBASE_AUTH_DOMAIN && env.VITE_FIREBASE_PROJECT_ID && env.VITE_FIREBASE_APP_ID);
const app = firebaseEnabled ? (getApps()[0] ?? initializeApp({apiKey:env.VITE_FIREBASE_API_KEY,authDomain:env.VITE_FIREBASE_AUTH_DOMAIN,projectId:env.VITE_FIREBASE_PROJECT_ID,appId:env.VITE_FIREBASE_APP_ID,storageBucket:env.VITE_FIREBASE_STORAGE_BUCKET,messagingSenderId:env.VITE_FIREBASE_MESSAGING_SENDER_ID})) : null;
const auth = app ? getAuth(app) : null;
const db = app ? getFirestore(app) : null;
export const login = async () => { if (!auth) throw Error('Firebase設定が必要です'); await signInWithPopup(auth,new GoogleAuthProvider()); };
export const logout = async () => { if (auth) await signOut(auth); };
export const listenAuth = (callback:(user:User|null)=>void) => auth ? onAuthStateChanged(auth,callback) : () => {};
export const firestore = () => { if (!db) throw Error('Firebase未設定'); return db; };

if (app && auth && db && import.meta.env.DEV && import.meta.env.VITE_USE_FIREBASE_EMULATORS === 'true') {
 connectAuthEmulator(auth,'http://127.0.0.1:9099',{disableWarnings:true});
 connectFirestoreEmulator(db,'127.0.0.1',8080);
}
