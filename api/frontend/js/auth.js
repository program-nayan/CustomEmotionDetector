const API="/api";
function switchTab(tab){
  document.querySelectorAll(".auth-tab").forEach(t=>t.classList.remove("active"));
  document.querySelectorAll(".auth-panel").forEach(p=>p.style.display="none");
  document.getElementById("tab-"+tab).classList.add("active");
  document.getElementById("panel-"+tab).style.display="block";
}
function togglePassword(id,btn){
  const inp=document.getElementById(id);
  inp.type=inp.type==="password"?"text":"password";
  btn.textContent=inp.type==="password"?"??":"??";
}
async function handleLogin(e){
  e.preventDefault();
  const btn=document.getElementById("btn-login");
  const err=document.getElementById("login-error");
  err.style.display="none";
  setLoading(btn,true);
  try{
    const r=await fetch(API+"/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({username:document.getElementById("login-username").value,
        password:document.getElementById("login-password").value})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||"Login failed");
    saveAuth(d);
    window.location.href="/chat.html";
  }catch(ex){showError(err,ex.message)}finally{setLoading(btn,false)}
}
async function handleSignup(e){
  e.preventDefault();
  const btn=document.getElementById("btn-signup");
  const err=document.getElementById("signup-error");
  err.style.display="none";
  setLoading(btn,true);
  try{
    const r=await fetch(API+"/auth/register",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({username:document.getElementById("signup-username").value,
        email:document.getElementById("signup-email").value||null,
        password:document.getElementById("signup-password").value})});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||"Registration failed");
    saveAuth(d);
    window.location.href="/chat.html";
  }catch(ex){showError(err,ex.message)}finally{setLoading(btn,false)}
}
async function handleAnonymous(){
  const btn=document.getElementById("btn-anon");
  btn.textContent="Starting...";btn.disabled=true;
  try{
    const r=await fetch(API+"/auth/anonymous",{method:"POST"});
    const d=await r.json();
    if(!r.ok)throw new Error("Failed");
    saveAuth(d);
    window.location.href="/chat.html?anon=true";
  }catch{btn.textContent="?? Continue Anonymously";btn.disabled=false}
}
function saveAuth(d){
  localStorage.setItem("serenity_token",d.access_token);
  localStorage.setItem("serenity_user",JSON.stringify({id:d.user_id,username:d.username}));
}
function showError(el,msg){el.textContent=msg;el.style.display="block"}
function setLoading(btn,on){
  btn.querySelector("span").style.display=on?"none":"";
  btn.querySelector(".btn-spinner").style.display=on?"inline-block":"none";
  btn.disabled=on;
}
// Handle #signup hash
if(window.location.hash==="#signup")switchTab("signup");
// Redirect if already logged in
const tok=localStorage.getItem("serenity_token");
if(tok)window.location.href="/chat.html";
