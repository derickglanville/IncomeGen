const root=document.documentElement;
const saved=localStorage.getItem('incomegen-theme');
if(saved) root.dataset.theme=saved;
document.querySelector('#theme-toggle')?.addEventListener('click',()=>{
  root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';
  localStorage.setItem('incomegen-theme',root.dataset.theme);
});
setTimeout(()=>document.querySelectorAll('.alert.success').forEach(x=>x.classList.add('fade')),5000);

