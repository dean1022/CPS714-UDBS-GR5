let loans=[];
let readerObjectUrl=null;

const list=document.querySelector('#my-loans');
function draw(){list.innerHTML='';document.querySelector('#loan-count').textContent=loans.length+' active '+(loans.length===1?'loan':'loans');document.querySelector('#empty-loans').hidden=!!loans.length;
 for(const loan of loans){const col=document.createElement('div');col.className='col-md-6 col-lg-4';// Render writes loan timestamps in UTC without an offset. Parse explicitly as UTC.
 const rawDue=String(loan.due_at || '').trim();
 const due=new Date(/[zZ]$|[+-]\d{2}:?\d{2}$/.test(rawDue) ? rawDue.replace(' ','T') : rawDue.replace(' ','T')+'Z');const remain=Number.isFinite(due.getTime()) ? Math.max(0,due.getTime()-Date.now()) : 0;const days=Math.floor(remain/86400000),hours=Math.floor((remain%86400000)/3600000),minutes=Math.floor((remain%3600000)/60000);
 col.innerHTML=`<article class="book-card"><h3>${safeText(loan.title)}</h3><p>Due: ${safeText(loan.due_at)}</p><p class="time-left">${days} days ${hours} hours ${minutes} minutes remaining</p><div class="card-bottom"><a class="btn btn-outline-dark details-btn" href="literature.html?id=${encodeURIComponent(loan.literature_id)}">View details</a><button class="btn btn-dark read-btn">Read PDF</button><button class="btn btn-outline-dark return-btn">Return early</button></div></article>`;
 col.querySelector('.read-btn').onclick=()=>openBook(loan);col.querySelector('.return-btn').onclick=()=>returnLoan(loan);list.appendChild(col);}}
async function loadLoans(){try{const d=await libraryRequest('loans');loans=d.loans;draw();}catch(e){showPageError(e);}}
function closeReader(){
 const frame=document.querySelector('#reading-pdf');frame.removeAttribute('src');
 if(readerObjectUrl){URL.revokeObjectURL(readerObjectUrl);readerObjectUrl=null;}
 document.querySelector('#reading-section').hidden=true;
}
async function openBook(loan){
 try{
  closeReader();
  const token=sessionStorage.getItem('udbs_token');
  const response=await fetch(libraryUrl+'/read/'+encodeURIComponent(loan.literature_id),{headers:{Authorization:'Bearer '+token},cache:'no-store'});
  if(!response.ok){let d=await response.json().catch(()=>({}));throw Error(d.detail||d.message||'Unable to read PDF');}
  const pdf=await response.blob();
  if(!pdf.type.includes('pdf'))throw Error('The server did not return a PDF.');
  readerObjectUrl=URL.createObjectURL(pdf);
  document.querySelector('#reading-title').textContent=loan.title;
  document.querySelector('#reading-pdf').src=readerObjectUrl;
  document.querySelector('#reading-section').hidden=false;
  document.querySelector('#reading-section').scrollIntoView();
 }catch(e){showPageError(e);}
}
async function returnLoan(loan){if(!confirm('Return '+loan.title+' early?'))return;try{await libraryRequest('return/'+loan.loan_id,{method:'POST'});closeReader();await loadLoans();}catch(e){showPageError(e);}}
document.querySelector('#close-reading').onclick=closeReader;
(async()=>{try{await checkLogin();document.querySelector('#private-content').hidden=false;await loadLoans();setInterval(()=>{if(!document.hidden)loadLoans();},30000);setInterval(()=>{if(!document.hidden)draw();},60000);}catch(e){showPageError(e);}})();
