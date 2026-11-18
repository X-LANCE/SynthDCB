(() => {
  "use strict";
  const el = id => document.getElementById(id);
  const data = benchmarkData;
  const models = new Map(data.models.map(model => [model.id, model]));
  const percent = model => model.passed / model.attempts * 100;
  const fixed = value => value.toFixed(1) + "%";
  const tooltip = el("plot-tooltip");

  function svg(parent, tag, attrs, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key,value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    parent.append(node);
    return node;
  }
  function showTip(text, point) {
    tooltip.textContent = text;
    tooltip.hidden = false;
    const box = tooltip.getBoundingClientRect();
    tooltip.style.left = Math.max(8, Math.min(innerWidth-box.width-8, point.x+12))+"px";
    const y = point.y + 14 + box.height < innerHeight ? point.y+14 : point.y-box.height-10;
    tooltip.style.top = Math.max(6, y)+"px";
  }
  function center(node) {
    const r = node.getBoundingClientRect();
    return {x:r.left+r.width/2, y:r.top+r.height/2};
  }
  function chartFrame(id,width,height,margins,min,max,ticks,label) {
    const chart = el(id);
    chart.setAttribute("viewBox", "0 0 "+width+" "+height);
    chart.replaceChildren();
    const {left,right,top,bottom}=margins;
    const edge=width-right, base=height-bottom;
    const y = value => base-(value-min)/(max-min)*(base-top);
    for (const tick of ticks) {
      svg(chart,"line",{x1:left,x2:edge,y1:y(tick),y2:y(tick),class:"grid-line"});
      svg(chart,"text",{x:left-8,y:y(tick)+4,"text-anchor":"end"},tick);
    }
    svg(chart,"line",{x1:left,x2:edge,y1:base,y2:base,class:"axis-line"});
    if(label)svg(chart,"text",{x:left,y:16,class:"axis-label"},label);
    return {chart,left,edge,base,top,y,width,height};
  }
  function xTick(frame,x,label) {
    svg(frame.chart,"text",{x,y:frame.base+20,"text-anchor":"middle"},label);
  }
  function pathFor(values,x,y) {
    return values.map((v,i)=>(i===0?"M":"L")+x(i).toFixed(2)+" "+y(v).toFixed(2)).join(" ");
  }
  function brand(parent,model,x,y,size) {
    return svg(parent,"image",{class:"brand-icon",href:model.logo,x:x-size/2,y:y-size/2,width:size,height:size,"aria-hidden":"true"});
  }
  function modelSymbol(parent,model,x,y,factor=1,color=model.theme.color) {
    const {symbol,size,hollow}=model.theme;
    return svg(parent,"path",{class:"model-symbol","data-symbol":symbol,d:data.symbols[symbol],
      transform:"translate("+x+" "+y+") scale("+size*factor+")",fill:hollow?"none":color,
      stroke:color,"stroke-width":1.15,"vector-effect":"non-scaling-stroke","aria-hidden":"true"});
  }
  function swatch(parent,model) {
    const icon=svg(parent,"svg",{viewBox:"0 0 18 18",width:18,height:18,"aria-hidden":"true"});
    modelSymbol(icon,model,9,9,1.25);
    parent.prepend(icon);
  }

  const modelMarks=[];
  let pinned=null, preview=null;
  function highlight() {
    const active=preview || pinned?.model;
    for (const mark of modelMarks) {
      mark.classList.toggle("is-active",mark.dataset.model===active);
      mark.classList.toggle("is-muted",Boolean(active && mark.dataset.model!==active));
      const {model,pricing}=mark.dataset;
      const pressed=model===pinned?.model && (!pricing || !pinned.pricing || pricing===pinned.pricing);
      mark.setAttribute("aria-pressed",String(pressed));
    }
  }
  function inspectModel(mark,point) {
    preview=mark.dataset.model; highlight(); showTip(mark.getAttribute("aria-label"),point);
  }
  function leaveModel() { preview=null; highlight(); tooltip.hidden=true; }
  function pinModel(mark) {
    const {model,pricing}=mark.dataset, label=mark.getAttribute("aria-label");
    pinned=pinned?.model===model && pinned.pricing===pricing ? null : {model,pricing};
    preview=null; highlight();
    el("model-status").textContent=pinned ? label : "Model selection cleared";
    if(!pinned) { tooltip.hidden=true; return; }
    showTip(label,center(mark));
    if(mark.ownerSVGElement.id!=="main-chart") {
      const bar=el("main-chart").querySelector('[data-model="'+model+'"]');
      const scroller=bar.closest(".chart-scroll");
      if(scroller.scrollWidth>scroller.clientWidth) scroller.scrollLeft+=center(bar).x-center(scroller).x;
    }
  }
  function modelMark(chart,model,label) {
    const mark=svg(chart,"g",{class:"mark","data-model":model.id,role:"button",tabindex:0,"aria-pressed":"false","aria-label":label});
    modelMarks.push(mark);
    if(chart.id==="main-chart") {
      mark.addEventListener("pointerenter",e=>inspectModel(mark,{x:e.clientX,y:e.clientY}));
      mark.addEventListener("pointerleave",leaveModel);
      mark.addEventListener("click",()=>pinModel(mark));
    }
    mark.addEventListener("focus",()=>inspectModel(mark,center(mark)));
    mark.addEventListener("blur",leaveModel);
    mark.addEventListener("keydown",e=>{
      if(e.key==="Enter" || e.key===" ") { e.preventDefault(); pinModel(mark); }
    });
    return mark;
  }

  function mainChart() {
    const f=chartFrame("main-chart",1184,377,{left:54,right:14,top:30,bottom:139},0,100,[0,25,50,75,100],"Test Pass@1 (%)");
    const step=(f.edge-f.left)/data.models.length;
    data.models.forEach((model,i)=>{
      const score=percent(model), x=f.left+step*(i+.5);
      const mark=modelMark(f.chart,model,model.name+" · "+fixed(score)+"  ("+model.passed.toLocaleString("en-US")+"/"+model.attempts.toLocaleString("en-US")+")");
      svg(mark,"rect",{x:x-step*.38,y:f.top,width:step*.76,height:f.base-f.top,fill:"transparent"});
      svg(mark,"rect",{class:"bar",fill:model.theme.color,x:x-step*.33,y:f.y(score),width:step*.66,height:f.base-f.y(score),rx:2});
      svg(mark,"text",{class:"bar-value",x,y:f.y(score)-6,"text-anchor":"middle"},score.toFixed(1));
      brand(mark,model,x-6,f.base+13,18);
      modelSymbol(mark,model,x+10,f.base+13,1);
      svg(mark,"text",{class:"bar-label",transform:"translate("+x+" "+(f.base+34)+") rotate(-52)","text-anchor":"end"},model.name);
    });
  }
  const costPoints=[], sizePoints=[];
  for(const model of data.models) {
    if(model.usdWithCache!==undefined) {
      costPoints.push({model,value:model.usdWithCache,pricing:"With cache"},
        {model,value:model.usdWithoutCache,pricing:"Without cache"});
    }
    if(model.parameters!==undefined)sizePoints.push({model,value:model.parameters/1e9});
  }
  function scatter(id,series,ticks,axisLabel) {
    const chart=el(id);
    const w=Math.max(280,Math.round(chart.getBoundingClientRect().width));
    const f=chartFrame(id,w,400,{left:39,right:26,top:32,bottom:54},0,100,[0,25,50,75,100],"Test Pass@1 (%)");
    const start=Math.log10(ticks[0]), span=Math.log10(ticks.at(-1))-start;
    const x=value=>f.left+(Math.log10(value)-start)/span*(f.edge-f.left);
    for(const t of ticks) xTick(f,x(t),String(t));
    svg(chart,"text",{x:(f.left+f.edge)/2,y:f.height-5,"text-anchor":"middle",class:"axis-label"},axisLabel);
    const points=[];
    for(const {model,value,pricing} of series) {
      const detail=pricing ? pricing+" · $"+value.toFixed(4)+" / attempt"
        : value.toLocaleString("en-US",{maximumFractionDigits:2})+"B parameters";
      const px=x(value),py=f.y(percent(model));
      const mark=modelMark(chart,model,model.name+" · "+fixed(percent(model))+"\n"+detail);
      if(pricing)mark.dataset.pricing=pricing;
      points.push({x:px,y:py,mark});
      svg(mark,"circle",{cx:px,cy:py,r:10,fill:"transparent",class:"scatter-dot"});
      svg(mark,"circle",{cx:px,cy:py,r:9,class:"point-ring","pointer-events":"none"});
      const color=pricing==="Without cache"?paperTint(model.theme.color,58):model.theme.color;
      modelSymbol(mark,model,px,py,1.3,color).setAttribute("pointer-events","none");
    }
    function nearby(event) {
      const cursor=new DOMPoint(event.clientX,event.clientY).matrixTransform(chart.getScreenCTM().inverse());
      return points.map(p=>({mark:p.mark,distance:Math.hypot(cursor.x-p.x,cursor.y-p.y)}))
        .filter(p=>p.distance<=10).sort((a,b)=>a.distance-b.distance);
    }
    chart.onpointermove=e=>{
      const [point]=nearby(e);
      if(point)inspectModel(point.mark,{x:e.clientX,y:e.clientY}); else leaveModel();
    };
    chart.onpointerleave=leaveModel;
    chart.onclick=e=>{
      if(e.detail===0) {
        const mark=e.target.closest(".mark");
        if(mark)pinModel(mark);
        return;
      }
      const hits=nearby(e);
      if(!hits.length)return;
      // Repeated clicks can select marks whose data positions resolve to the same pixel.
      const tied=hits.filter(p=>p.distance-hits[0].distance<1);
      const selected=tied.findIndex(p=>p.mark.dataset.model===pinned?.model && p.mark.dataset.pricing===pinned.pricing);
      pinModel(tied[(selected+1)%tied.length].mark);
    };
  }

  const grid=el("budget-grid"), reduced=matchMedia("(prefers-reduced-motion: reduce)");
  const panels=Object.entries(data.budget).map(([id,curves])=>{
    const model=models.get(id);
    const figure=document.createElement("figure"), caption=document.createElement("figcaption");
    const delta=document.createElement("span");
    caption.textContent=model.name;
    swatch(caption,model);
    delta.className="budget-delta";
    figure.append(caption,delta);
    const drawing=svg(figure,"svg",{id:"budget-"+id,class:"plot budget-plot",role:"group","aria-label":model.name+" goal success"});
    grid.append(figure);
    return {model,curves,delta,drawing};
  });
  let selectedTurn=null, revealed=0, readyToReveal=false;

  function budgetReveal() {
    if(!readyToReveal || !panels[0].clip)return;
    const plot=panels[0].drawing.getBoundingClientRect();
    const progress=(innerHeight*.96-plot.top)/Math.max(1,Math.min(innerHeight*.52,plot.height));
    revealed=reduced.matches?1:Math.max(revealed,Math.min(1,Math.max(0,progress)));
    for(const p of panels)p.clip.setAttribute("width",p.clipWidth*revealed);
  }
  function inspection(turn) {
    selectedTurn=turn;
    el("budget-turn").textContent=turn===null?"":"Turn "+(turn+1);
    for(const p of panels) {
      p.guide.setAttribute("visibility",turn===null?"hidden":"visible");
      if(turn===null) { p.delta.textContent=""; continue; }
      const original=p.curves.cumulative[turn]*100, truncated=p.curves.stop_at_k[turn]*100;
      const gap=truncated-original, x=p.x(turn), a=p.y(original), b=p.y(truncated);
      p.guide.setAttribute("transform","translate("+x+" 0)");
      p.gap.setAttribute("y1",a); p.gap.setAttribute("y2",b);
      p.originalPoint.setAttribute("cy",a); p.truncatedPoint.setAttribute("cy",b);
      p.delta.textContent="Δ "+(gap>0?"+":"")+gap.toFixed(1)+" pp";
      p.hit.setAttribute("aria-valuenow",turn+1);
      p.hit.setAttribute("aria-valuetext","Turn "+(turn+1)+", original "+fixed(original)+", truncated "+fixed(truncated)+", "+p.delta.textContent);
    }
  }
  function paperTint(hex,whitePercent) {
    const white=whitePercent/100, original=(100-whitePercent)/100;
    const channels=[1,3,5].map(start=>Math.round(255*white+original*parseInt(hex.slice(start,start+2),16)));
    return "rgb("+channels.join(",")+")";
  }
  function budgetChart() {
    for(const p of panels) {
      const width=Math.round(p.drawing.getBoundingClientRect().width);
      const f=chartFrame(p.drawing.id,width,186,{left:29,right:10,top:12,bottom:31},0,100,[0,50,100]);
      p.x=i=>f.left+(f.edge-f.left)*i/49;
      p.y=f.y;
      for(const turn of (width<205?[1,25,50]:[1,10,20,30,40,50]))xTick(f,p.x(turn-1),turn);
      const clipId="reveal-"+p.model.id;
      const clip=svg(svg(f.chart,"defs",{}),"clipPath",{id:clipId,clipPathUnits:"userSpaceOnUse"});
      p.clipWidth=f.edge-f.left+4;
      p.clip=svg(clip,"rect",{x:f.left-2,y:f.top-2,width:p.clipWidth*revealed,height:f.base-f.top+4});
      const curves=svg(f.chart,"g",{"clip-path":"url(#"+clipId+")",class:"budget-curves"});
      const color=p.model.theme.color, truncatedColor=paperTint(color,58);
      for(const [key,stroke] of [["stop_at_k",truncatedColor],["cumulative",color]]){
        svg(curves,"path",{class:"curve","data-metric":key,stroke,d:pathFor(p.curves[key],p.x,v=>p.y(v*100))});
      }
      p.guide=svg(f.chart,"g",{class:"turn-guide",visibility:"hidden","pointer-events":"none","aria-hidden":"true"});
      svg(p.guide,"line",{x1:0,x2:0,y1:f.top,y2:f.base,stroke:"#7d898b","stroke-dasharray":"3 4",opacity:.7});
      p.gap=svg(p.guide,"line",{class:"turn-gap",x1:0,x2:0,stroke:paperTint(color,28),"stroke-width":2,"stroke-dasharray":"2 2"});
      p.originalPoint=svg(p.guide,"circle",{cx:0,r:2.8,fill:color});
      p.truncatedPoint=svg(p.guide,"circle",{cx:0,r:2.8,fill:truncatedColor,stroke:color,"stroke-width":1});
      p.hit=svg(f.chart,"rect",{x:f.left,y:f.top,width:f.edge-f.left,height:f.base-f.top,fill:"transparent",
        tabindex:0,role:"slider","aria-label":p.model.name+" interaction turn","aria-valuemin":1,"aria-valuemax":50,"aria-valuenow":1});
      function pointToTurn(e) {
        const r=p.hit.getBoundingClientRect();
        inspection(Math.max(0,Math.min(49,Math.round((e.clientX-r.left)/r.width*49))));
      }
      p.hit.addEventListener("pointermove",pointToTurn);
      p.hit.addEventListener("pointerdown",pointToTurn);
      p.hit.addEventListener("pointerleave",e=>{
        if(e.pointerType==="mouse" && document.activeElement!==p.hit)inspection(null);
      });
      p.hit.addEventListener("focus",()=>inspection(selectedTurn??0));
      p.hit.addEventListener("blur",()=>inspection(null));
      p.hit.addEventListener("keydown",e=>{
        const turn=selectedTurn??0;
        const next={ArrowLeft:turn-1,ArrowRight:turn+1,ArrowUp:turn+1,ArrowDown:turn-1,Home:0,End:49}[e.key];
        if(next!==undefined){e.preventDefault();inspection(Math.max(0,Math.min(49,next)));}
        else if(e.key==="Escape")inspection(null);
      });
    }
    inspection(selectedTurn); budgetReveal();
  }
  // Task-wall layout and web fonts affect the budget section's initial scroll position.
  window.addEventListener("DOMContentLoaded",async()=>{
    await document.fonts.ready;
    requestAnimationFrame(()=>{readyToReveal=true;budgetReveal();});
  },{once:true});

  const valid=data.validation, visible=new Set(valid.models);
  function styleChart() {
    const domain=el("style-domain").value, delta=el("chart-metric").value==="delta";
    const rows=valid.passed[domain], n=valid.tasks[domain];
    const values=rows.map(row=>row.map((v,i)=>(v-(delta?rows[0][i]:0))*100/n));
    const low=delta?Math.min(-10,Math.floor(Math.min(...values.flat())/10)*10):0;
    const high=delta?Math.max(10,Math.ceil(Math.max(...values.flat())/10)*10):100;
    const ticks=delta?Array.from({length:1+(high-low)/10},(_,i)=>low+i*10):[0,25,50,75,100];
    const {width,height}=el("style-chart").getBoundingClientRect();
    const f=chartFrame("style-chart",width,height,{left:42,right:15,top:30,bottom:88},low,high,ticks,delta?"Change from Template (pp)":"Validation Pass@1 (%)");
    const step=(f.edge-f.left-20)/7, x=i=>f.left+10+step*i;
    valid.models.forEach((id,i)=>{
      if(!visible.has(id)) return;
      const series=svg(f.chart,"g",{"data-series":id});
      const model=models.get(id);
      svg(series,"path",{class:"curve",stroke:model.theme.color,d:pathFor(values.map(row=>row[i]),x,f.y)});
      values.forEach((row,j)=>modelSymbol(series,model,x(j),f.y(row[i]),1.2));
    });
    valid.styles.forEach((name,j)=>{
      svg(f.chart,"text",{transform:"translate("+x(j)+" "+(f.base+15)+") rotate(-50)","text-anchor":"end"},name);
      const left=Math.max(f.left,x(j)-step/2), right=Math.min(f.edge,x(j)+step/2);
      const hit=svg(f.chart,"rect",{x:left,y:f.top,width:right-left,height:f.base-f.top+20,fill:"transparent",tabindex:0,role:"img"});
      const readout=valid.models.flatMap((id,i)=>visible.has(id)?[models.get(id).name+"  "+values[j][i].toFixed(1)+(delta?" pp":"%")]:[]);
      const label=name+" · "+domain+"\n"+readout.join("\n");
      hit.setAttribute("aria-label",label);
      hit.addEventListener("pointerenter",e=>showTip(label,{x:e.clientX,y:e.clientY}));
      hit.addEventListener("click",e=>showTip(label,{x:e.clientX,y:e.clientY}));
      hit.addEventListener("focus",()=>showTip(label,center(hit)));
      hit.addEventListener("pointerleave",()=>tooltip.hidden=true);
      hit.addEventListener("blur",()=>tooltip.hidden=true);
    });
  }
  valid.models.forEach(id=>{
    const b=document.createElement("button"); b.type="button"; b.textContent=models.get(id).name; swatch(b,models.get(id));
    b.setAttribute("aria-pressed","true");
    b.addEventListener("click",()=>{
      if(visible.has(id)) visible.delete(id); else visible.add(id);
      b.setAttribute("aria-pressed",String(visible.has(id))); styleChart();
    });
    el("style-legend").append(b);
  });
  el("chart-metric").addEventListener("change",styleChart);
  el("style-domain").addEventListener("change",styleChart);
  new ResizeObserver(styleChart).observe(el("style-chart").parentElement);
  function draw() {
    tooltip.hidden=true; modelMarks.length=0; preview=null;
    mainChart();
    scatter("cost-chart",costPoints,[.001,.01,.1,1],"USD per attempt · log scale");
    scatter("size-chart",sizePoints,[.1,1,10,100,1000],"Parameters (billions) · log scale");
    budgetChart(); highlight();
  }
  draw();
  let lastWidth=innerWidth;
  window.addEventListener("resize",()=>{
    if(innerWidth!==lastWidth) { lastWidth=innerWidth; draw(); }
    else budgetReveal();
  });
  window.addEventListener("scroll",()=>{budgetReveal();tooltip.hidden=true;},{passive:true});
  reduced.addEventListener("change",budgetReveal);

  let openInfo=null;
  function setInfo(button,open) {
    if(open && openInfo && openInfo!==button) setInfo(openInfo,false);
    el(button.getAttribute("aria-controls")).hidden=!open;
    button.setAttribute("aria-expanded",String(open));
    openInfo=open?button:null;
  }
  for(const info of document.querySelectorAll(".info")) {
    const button=info.querySelector("button");
    let pinnedInfo=false;
    info.addEventListener("pointerenter",e=>{if(e.pointerType==="mouse")setInfo(button,true);});
    info.addEventListener("pointerleave",()=>{if(!pinnedInfo)setInfo(button,false);});
    button.addEventListener("focus",()=>setInfo(button,true));
    button.addEventListener("blur",()=>{pinnedInfo=false;setInfo(button,false);});
    button.addEventListener("click",()=>{pinnedInfo=!pinnedInfo;setInfo(button,pinnedInfo);});
  }
  const nav=document.querySelector(".research-nav"), navToggle=nav.querySelector(".nav-toggle");
  const research=nav.querySelector(".research-dropdown"), summary=research.querySelector("summary");
  const hoverNav=matchMedia("(min-width: 1024px) and (hover: hover)");
  let openedOnHover=false;
  function closeResearch() { research.open=false; openedOnHover=false; }
  function setNav(open) {
    navToggle.setAttribute("aria-expanded",String(open));
    if(!open)closeResearch();
  }
  navToggle.addEventListener("click",()=>setNav(navToggle.getAttribute("aria-expanded")!=="true"));
  matchMedia("(min-width: 1024px)").addEventListener("change",()=>setNav(false));
  research.addEventListener("pointerenter",e=>{
    if(hoverNav.matches && e.pointerType==="mouse" && !research.open) {
      research.open=true; openedOnHover=true;
    }
  });
  summary.addEventListener("click",e=>{
    if(openedOnHover && e.detail>0)e.preventDefault();
    openedOnHover=false;
  });
  research.addEventListener("pointerleave",()=>{
    if(openedOnHover && !research.matches(":focus-within"))closeResearch();
  });
  nav.addEventListener("focusout",e=>{
    if(!nav.contains(e.relatedTarget))setNav(false);
    else if(!research.contains(e.relatedTarget))closeResearch();
  });
  document.addEventListener("click",e=>{
    if(!nav.contains(e.target) || e.target.closest(".nav-menu a"))setNav(false);
    else if(!research.contains(e.target))closeResearch();
    if(openInfo && !openInfo.parentElement.contains(e.target))setInfo(openInfo,false);
  });
  document.addEventListener("keydown",e=>{
    if(e.key!=="Escape") return;
    if(openInfo)setInfo(openInfo,false);
    if(research.open){closeResearch();summary.focus();}
    else if(navToggle.getAttribute("aria-expanded")==="true"){setNav(false);navToggle.focus();}
    pinned=null; preview=null; highlight(); tooltip.hidden=true;
  });
  el("copy-citation").addEventListener("click",async()=>{
    const source=el("bibtex"),status=el("copy-status");
    try { await navigator.clipboard.writeText(source.textContent); status.textContent="BibTeX copied."; }
    catch {
      const range=document.createRange(); range.selectNodeContents(source);
      const selection=window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
      status.textContent="BibTeX selected for copying.";
    }
  });
})();
