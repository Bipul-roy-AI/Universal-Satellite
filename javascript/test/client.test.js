import test from 'node:test';
import assert from 'node:assert/strict';
import {computeIndex,Client,indices} from '../index.js';
test('known index values and invalid math',()=>{
 assert.ok(Math.abs(computeIndex('ndvi',{nir:.8,red:.2})-.6)<1e-12);
 assert.deepEqual(computeIndex('ndvi',{nir:[.8,0],red:[.2,0]}).map(x=>Number.isNaN(x)?null:Math.round(x*10)/10),[.6,null]);
 assert.throws(()=>computeIndex('ndvi',{nir:[1,2],red:1}),/shapes/);
 assert.throws(()=>computeIndex('ndvi',{nir:1,red:2},{unknown:1}),/coefficient/);
 assert.throws(()=>computeIndex('ndgi',{nir:.8,red:.2,green:.4}),/coefficient/);
 assert.equal(Object.keys(indices).length,280);
});
test('Python bridge returns catalog and structured errors',async()=>{
 const client=new Client();
 const sources=await client.sources();
 assert.ok(sources.some(x=>x.id==='smap-l4'));
 await assert.rejects(client.search({dataset:'unknown',bbox:[0,0,1,1],start:'2024-01-01',end:'2024-01-02'}),/Unknown dataset/);
});
test('missing engine is actionable',async()=>{
 await assert.rejects(new Client({python:'/missing/python'}).sources());
});

test('all 280 formulas match Python scalar fixtures',async()=>{
 const {readFileSync}=await import('node:fs');
 const cases=JSON.parse(readFileSync(new URL('./parity.json',import.meta.url)));
 for(const row of cases){
  const actual=computeIndex(row.name,row.bands,row.constants);
  if(row.expected===null)assert.ok(Number.isNaN(actual),row.name);
  else assert.ok(Math.abs(actual-row.expected)<=1e-10*Math.max(1,Math.abs(row.expected)),row.name);
 }
 assert.equal(cases.length,280);
});
