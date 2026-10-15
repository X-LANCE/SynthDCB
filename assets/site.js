document.getElementById('copy-citation').addEventListener('click',async()=>{const status=document.getElementById('copy-status');try{await navigator.clipboard.writeText(document.getElementById('bibtex').textContent);status.textContent='BibTeX copied.';}catch{status.textContent='Select the BibTeX text below to copy it.';const range=document.createRange();range.selectNodeContents(document.getElementById('bibtex'));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);}});
const navToggle=document.querySelector('.nav-toggle');
const navigation=document.getElementById('research-navigation');
const researchDropdown=document.querySelector('.research-dropdown');
navToggle.addEventListener('click',()=>{const expanded=navToggle.getAttribute('aria-expanded')!=='true';navToggle.setAttribute('aria-expanded',String(expanded));navigation.classList.toggle('is-open',expanded);});
document.addEventListener('click',event=>{if(!researchDropdown.contains(event.target))researchDropdown.open=false;});
document.addEventListener('keydown',event=>{if(event.key==='Escape'){researchDropdown.open=false;navigation.classList.remove('is-open');navToggle.setAttribute('aria-expanded','false');if(innerWidth<=1023)navToggle.focus();else researchDropdown.querySelector('summary').focus();}});
