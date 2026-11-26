/* Local-only data adapter. It never sends state to, or impersonates, the API. */
"use strict";
window.TopologyMockAdapter = Object.freeze({
  presets: {
    basic: { routers:["A","B","C","D"], links:[["A","B",1],["A","C",2],["B","D",1],["C","D",3]] },
    medium: { routers:["R1","R2","R3","R4","R5","R6","R7","R8"], links:[["R1","R2",2],["R2","R3",1],["R3","R4",2],["R4","R5",1],["R5","R6",2],["R6","R7",1],["R7","R8",2],["R8","R1",3],["R1","R5",4],["R2","R6",3],["R3","R7",4],["R4","R8",3]] },
    large: { routers:Array.from({length:12},(_,i)=>`R${i+1}`), links:[["R1","R2",2],["R2","R3",1],["R3","R4",2],["R4","R5",1],["R5","R6",2],["R6","R7",1],["R7","R8",2],["R8","R9",1],["R9","R10",2],["R10","R11",1],["R11","R12",2],["R12","R1",3],["R1","R7",4],["R2","R8",3],["R3","R9",4],["R4","R10",3],["R5","R11",4],["R6","R12",3]] },
  },
  copy(topology) { return JSON.parse(JSON.stringify(topology)); },
  preset(name) {
    const preset=this.presets[name];
    if(!preset) throw new Error(`Unknown topology preset: ${name}`);
    return {routers:preset.routers.map(id=>({id})),links:preset.links.map(([source,target,cost])=>({id:`${source}-${target}`,source,target,cost,active:true}))};
  },
  validate(topology) {
    if(!topology||!Array.isArray(topology.routers)||!Array.isArray(topology.links))return false;
    const ids=topology.routers.map(r=>r?.id);
    if(ids.some(id=>typeof id!=="string"||!id.trim())||new Set(ids).size!==ids.length)return false;
    const known=new Set(ids),linkIds=new Set();
    return topology.links.every(l=>l&&typeof l.id==="string"&&l.id.trim()&&!linkIds.has(l.id)&&(linkIds.add(l.id),known.has(l.source)&&known.has(l.target)&&l.source!==l.target&&Number.isInteger(l.cost)&&l.cost>0&&typeof l.active==="boolean"));
  },
});
