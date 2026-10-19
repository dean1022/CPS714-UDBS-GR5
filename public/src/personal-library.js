let loans=[];
let readingPdf=null;
let readerGeneration=0;
const PDF_JS_URL='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.min.mjs';
const PDF_WORKER_URL='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.worker.min.mjs';
let pdfJsPromise=null;
function getPdfJs(){
 if(!pdfJsPromise) pdfJsPromise=import(PDF_JS_URL).then(mod=>{
  mod.GlobalWorkerOptions.workerSrc=PDF_WORKER_URL;
  return mod;
 });
 return pdfJsPromise;
}

const list=document.querySelector('#my-loans');
function draw(){list.innerHTML='';document.querySelector('#loan-count').textContent=loans.length+' active '+(loans.length===1?'loan':'loans');document.querySelector('#empty-loans').hidden=!!loans.length;
 for(const loan of loans){const col=document.createElement('div');col.className='col-md-6 col-lg-4';// Render writes loan timestamps in UTC without an offset. Parse explicitly as UTC.
 const rawDue=String(loan.due_at || '').trim();
 const due=new Date(/[zZ]$|[+-]\d{2}:?\d{2}$/.test(rawDue) ? rawDue.replace(' ','T') : rawDue.replace(' ','T')+'Z');const remain=Number.isFinite(due.getTime()) ? Math.max(0,due.getTime()-Date.now()) : 0;const days=Math.floor(remain/86400000),hours=Math.floor((remain%86400000)/3600000),minutes=Math.floor((remain%3600000)/60000);
 col.innerHTML=`<article class="book-card"><h3>${safeText(loan.title)}</h3><p>Due: ${safeText(loan.due_at)}</p><p class="time-left">${days} days ${hours} hours ${minutes} minutes remaining</p><div class="card-bottom"><a class="btn btn-outline-dark details-btn" href="literature.html?id=${encodeURIComponent(loan.literature_id)}">View details</a><button class="btn btn-dark read-btn">Read PDF</button><button class="btn btn-outline-dark return-btn">Return early</button></div></article>`;
 col.querySelector('.read-btn').onclick=()=>openBook(loan);col.querySelector('.return-btn').onclick=()=>returnLoan(loan);list.appendChild(col);}}
async function loadLoans(){try{const d=await libraryRequest('loans');loans=d.loans;draw();}catch(e){showPageError(e);}}
function closeReader(){
 readerGeneration++;
 if(readingPdf){readingPdf.destroy();readingPdf=null;}
 document.querySelector('#pdf-pages').replaceChildren();
 document.querySelector('#pdf-loading').textContent='';
 document.querySelector('#reading-section').hidden=true;
}
async function openBook(loan){
 try{
  closeReader();
  let generation=readerGeneration;
  const token=sessionStorage.getItem('udbs_token');
  const response=await fetch(libraryUrl+'/read/'+encodeURIComponent(loan.literature_id),{headers:{Authorization:'Bearer '+token},cache:'no-store'});
  if(!response.ok){let d=await response.json().catch(()=>({}));throw Error(d.detail||d.message||'Unable to read PDF');}
  const pdfBytes=new Uint8Array(await response.arrayBuffer());
  if(generation!==readerGeneration)return;
  document.querySelector('#reading-title').textContent=loan.title;
  const pages=document.querySelector('#pdf-pages');
  document.querySelector('#reading-section').hidden=false;
  const loading=document.querySelector('#pdf-loading');
  loading.textContent='Loading book pages...';
  const pdfjs=await getPdfJs();
  if(generation!==readerGeneration)return;
  const doc=await pdfjs.getDocument({data:pdfBytes}).promise;
  if(generation!==readerGeneration){await doc.destroy();return;}
  readingPdf=doc;
  // Render each page onto a canvas instead of using the browser PDF viewer.
  // This does not add any printing, saving or Drive interface controls.
  for(let number=1;number<=doc.numPages;number++){
   if(generation!==readerGeneration)return;
   const page=await doc.getPage(number);
   const base=page.getViewport({scale:1});
   const width=Math.min(pages.clientWidth-16,850);
   const scale=Math.min(2,Math.max(0.5,width/base.width));
   const viewport=page.getViewport({scale});
   const canvas=document.createElement('canvas');
   canvas.className='pdf-page';
   canvas.width=Math.ceil(viewport.width);
   canvas.height=Math.ceil(viewport.height);
   canvas.setAttribute('aria-label','Page '+number+' of '+doc.numPages);
   pages.appendChild(canvas);
   await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;
  }
  if(generation===readerGeneration)loading.textContent='';
  document.querySelector('#reading-section').scrollIntoView({behavior:'smooth'});
 }catch(e){document.querySelector('#pdf-loading').textContent='';showPageError(e);}
}
async function returnLoan(loan){if(!confirm('Return '+loan.title+' early?'))return;try{await libraryRequest('return/'+loan.loan_id,{method:'POST'});closeReader();await loadLoans();}catch(e){showPageError(e);}}
document.querySelector('#close-reading').onclick=closeReader;
(async()=>{try{await checkLogin();document.querySelector('#private-content').hidden=false;await loadLoans();setInterval(()=>{if(!document.hidden)loadLoans();},30000);setInterval(()=>{if(!document.hidden)draw();},60000);}catch(e){showPageError(e);}})();
