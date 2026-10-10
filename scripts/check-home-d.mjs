// Run: node scripts/check-home-d.mjs /absolute/path/to/three-package
// Uses the same Three.js 0.169.0 package as the app; no browser or build required.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const pkg = path.resolve(process.argv[2] || 'node_modules/three');
const THREE = await import(pathToFileURL(path.join(pkg, 'build/three.module.js')));
const { RoundedBoxGeometry } = await import(pathToFileURL(path.join(pkg, 'examples/jsm/geometries/RoundedBoxGeometry.js')));
const { mergeGeometries } = await import(pathToFileURL(path.join(pkg, 'examples/jsm/utils/BufferGeometryUtils.js')));
const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const embedded = JSON.parse(html.match(/id="wattswrong-data">(.*?)<\/script>/s)[1]);
const run = code => vm.runInContext(code, context);
const context = vm.createContext({ THREE, RoundedBoxGeometry, mergeGeometries, assert, embedded, console });
run(html.slice(html.indexOf('const HOUR='), html.indexOf('window.WattsWrong=')));
run(`Data.load(embedded);
let world=new THREE.Group(),interior=null,selected=null,objects=[],houses=[],statuses=[],rooms=[],roomElements=[];
const geometryCache=new Map(),sharedMaterials=new Set(),sharedTextures=new Set(),materialCache=new Map();
const M={};let modelPromise=Promise.resolve(null);
const document={createElement:()=>({getContext:()=>({fillRect(){},fillText(){}})})};
const $=()=>({replaceChildren(){}});function setFloor(){}
`);
run(html.slice(html.indexOf('function material('), html.indexOf('// ==================== VIEW CONTROLLER')));
// Extract these existing lifecycle functions without executing browser startup.
run(html.slice(html.indexOf('function updateStatus('), html.indexOf('// Cheap per-frame')));
run(html.slice(html.indexOf('function disposeInterior('), html.indexOf('function leaveHome(')));
run(`for(const name of ['tile','wood','trim','plaster','steel','dark','roof','white','black','ceramic','fabric','fabricBlue','rug','door','glass','bark','leaf'])M[name]=material('#aaaaaa');
const h={id:Data.siteAt(3),root:new THREE.Group()};
const channels=Data.site(h.id).channels;
assert(hasGarage(h.id));assert(!hasGarage(null));
for(const i of [0,1])assert(!hasGarage(Data.siteAt(i)));
const exterior=garageExterior(h.root,M.plaster);
assert(exterior.children.length<10,'roller slats should be batched');
for(let iteration=0;iteration<3;iteration++){
 buildInterior(h);
 const root=interior.root,garage=interior.garage;
 assert.equal(garage.parent,interior.ground);
 assert.deepEqual(objects.filter(o=>o.channel).map(o=>o.channel).sort(),[...channels].sort());
 const garageObjects=objects.filter(o=>o.root.parent===garage);
 assert.deepEqual(garageObjects.map(o=>o.channel).sort(),['garage_freezer','garage_fridge']);
 assert.equal(objects.find(o=>o.channel==='fridge_freezer').root.parent,rooms.find(r=>r.name==='Kitchen · dining').g);
 root.scale.setScalar(1.5);root.updateMatrixWorld(true);
 assert.equal(garage.getWorldScale(new THREE.Vector3()).x,1.5);
 for(const channel of channels){
  const f=Data.findings.find(f=>f.site===h.id&&f.channel===channel);
  const s=statuses.find(s=>s.object.channel===channel);
  Data.time=f.detected;updateStatus();assert(s.level>0);
  for(const mesh of s.body){assert(mesh.material.emissiveIntensity>0);assert.equal(mesh.material.emissive.getHexString(),new THREE.Color(COLORS[s.level]).getHexString());assert(!sharedMaterials.has(mesh.material));}
  Data.time=Data.start;updateStatus();assert.equal(s.level,0);
  for(const mesh of s.body)assert.equal(mesh.material.emissiveIntensity,0);
 }
 const disposable=new Set(),shared=new Set([...sharedMaterials,...geometryCache.values()]);
 root.traverse(o=>{if(o.geometry&&!shared.has(o.geometry))disposable.add(o.geometry);if(o.material)for(const m of(Array.isArray(o.material)?o.material:[o.material]))if(!shared.has(m))disposable.add(m)});
 let disposed=0;for(const resource of disposable)resource.addEventListener('dispose',()=>disposed++);
 const fail=()=>assert.fail('shared resource disposed');for(const resource of shared)resource.addEventListener('dispose',fail);
 disposeInterior();
 assert.equal(disposed,disposable.size);assert.equal(root.parent,null);assert.equal(interior,null);assert.equal(objects.length,0);assert.equal(statuses.length,0);assert.equal(rooms.length,0);
 assert.equal(exterior.parent,h.root);
 for(const resource of shared)resource.removeEventListener('dispose',fail);
}
for(let i=0;i<3;i++){
 buildInterior({id:Data.siteAt(i),root:new THREE.Group()});
 assert.equal(!!interior.garage,i===2);
 const expected=[['aggregate','electric_heater','freezer_1','freezer_2','fridge'],['aggregate','freezer','fridge_freezer'],['aggregate','chest_freezer','fridge_freezer','kmix']][i];
 assert.deepEqual(objects.filter(o=>o.channel).map(o=>o.channel).sort(),expected);
 disposeInterior();
}
// Keep each tree's trunk and foliage together when batching the neighbourhood,
// so hiding/restoring a nearby tree never leaves detached branches visible.
tree(world,28,-7);const treeRoot=world.children.at(-1),parts=[...treeRoot.children];
batch(world);assert(parts.every(part=>part.parent===treeRoot));
console.log('PASS: channel placement, batching, scaling, real replay tint/reset, three build/dispose cycles, and A/B/C layouts');
`);
