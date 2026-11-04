import {readFileSync} from 'node:fs';
import {spawn} from 'node:child_process';
export const indices = JSON.parse(readFileSync(new URL('./data/indices.json',import.meta.url)));
export const constants = JSON.parse(readFileSync(new URL('./data/constants.json',import.meta.url)));
const aliases={A:'aerosol',B:'blue',G:'green',G1:'green1',R:'red',RE1:'rededge',RE2:'rededge2',RE3:'rededge3',N:'nir',N2:'nir08',S1:'swir16',S2:'swir22',T:'thermal',T1:'thermal1',Y:'yellow',VV:'vv',VH:'vh',HH:'hh',HV:'hv'};
function calc(node,values){
  if ('number' in node) return node.number;
  if ('symbol' in node) return values[node.symbol];
  const a=calc(node.a,values);
  if(node.op==='neg')return -a;
  if(node.op==='pos')return a;
  const b=calc(node.b,values);
  switch(node.op){case 'Add':return a+b;case 'Sub':return a-b;case 'Mult':return a*b;case 'Div':return a/b;case 'Pow':return a**b;default:throw new Error('Unsupported formula');}
}
export function computeIndex(name,bands,overrides={}){
  const spec=Object.hasOwn(indices,name)?indices[name]:Object.hasOwn(indices,name.toLowerCase())?indices[name.toLowerCase()]:undefined;if(!spec)throw new Error(`Unknown index ${name}`);
  const required=spec.bands.filter(x=>!(x in constants));
  const params=spec.bands.filter(x=>x in constants);
  if(Object.keys(bands).length!==required.length || required.some(k=>!Object.hasOwn(bands,aliases[k]||k)))throw new Error('Supply exactly the required bands');
  if(Object.keys(overrides).some(k=>!params.includes(k)))throw new Error('Unknown coefficient');
  const values={};
  for(const key of params){
    const v=Object.hasOwn(overrides,key)?overrides[key]:key==='n'?null:constants[key].default;
    if(typeof v!=='number'||!Number.isFinite(v))throw new Error(`Supply finite coefficient ${key}`);
    values[key]=v;
  }
  const inputs=required.map(k=>bands[aliases[k]||k]);
  const isArray=Array.isArray(inputs[0]);
  const length=isArray?inputs[0].length:1;
  if(inputs.some(x=>Array.isArray(x)!==isArray || (isArray&&x.length!==length)))throw new Error('Inputs must have equal shapes');
  function one(i){
    for(let j=0;j<required.length;j++){
      const v=isArray?inputs[j][i]:inputs[j];
      if(typeof v!=='number')throw new Error('Band values must be numbers');
      if(!Number.isFinite(v))return NaN;
      values[required[j]]=v;
    }
    const result=calc(spec.expression,values);return Number.isFinite(result)?result:NaN;
  }
  return isArray?Array.from({length},(_,i)=>one(i)):one(0);
}

export class Client{
  constructor({python=process.env.UNIVERSAL_SATELLITE_PYTHON||'python',signal}={}){this.python=python;this.signal=signal;}
  call(action,params={}){
    return new Promise((resolve,reject)=>{
      const child=spawn(this.python,['-m','universal_satellite.rpc'],{stdio:['pipe','pipe','pipe'],signal:this.signal});
      let output='',error='',settled=false;
      const fail=e=>{if(!settled){settled=true;reject(e);}};
      child.on('error',fail);child.stdin.on('error',fail);
      child.stdout.on('data',b=>{output+=b;if(output.length>64*1024*1024){child.kill();fail(new Error('Response exceeds 64 MiB'));}});
      child.stderr.on('data',b=>{if(error.length<4096)error+=b;});
      child.on('close',code=>{
        if(settled)return;
        try{const data=JSON.parse(output);if(code!==0||data.error)throw new Error(data.error||'Engine failed');settled=true;resolve(data.result);}
        catch(e){fail(new Error(output?e.message:'Python engine unavailable; install universal-satellite in the selected Python environment'));}
      });
      child.stdin.end(JSON.stringify({action,params}));
    });
  }
  sources(params={}){return this.call('sources',params);}
  search(params){return this.call('search',params);}
  environment(kind,params){return this.call('environment',{kind,...params});}
  weather(params){return this.call('weather',params);}
  download(params){return this.call('download',params);}
  summary(manifest){return this.call('summary',{manifest});}
  rasterIndex(name,output,bands,constants={}){return this.call('index',{name,output,bands,constants});}
  crop(params){return this.call('crop',params);}
  toa(params){return this.call('toa',params);}
  computeIndex(name,bands,constants={}){return computeIndex(name,bands,constants);}
}
