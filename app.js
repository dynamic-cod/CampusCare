const seed = [
  {id: "CC-1042", title: "Fan not working", category: "Electrical", location: "Academic Block A · Room 204", status: "In progress", priority: "High", date: "Today"},
  {id: "CC-1039", title: "Leaking water tap", category: "Plumbing", location: "Hostel 3 · Second floor", status: "Open", priority: "Normal", date: "Yesterday"},
  {id: "CC-1031", title: "Wi-Fi connectivity issue", category: "Internet & IT", location: "Central Library · Reading Hall", status: "Resolved", priority: "Normal", date: "Aug 24"},
  {id: "CC-1027", title: "Classroom needs cleaning", category: "Cleaning", location: "Academic Block B · Room 101", status: "Resolved", priority: "Normal", date: "Aug 22"}
];
let complaints = JSON.parse(localStorage.getItem("campusCareComplaints") || "null") || seed;
let currentFilter = "All";
const icons = {Electrical:"⚡", Plumbing:"⌁", Cleaning:"✦", "Internet & IT":"⌁", Furniture:"▤", Other:"!"};
const slug = value => value.toLowerCase().replaceAll(" ", "-");

function save(){ localStorage.setItem("campusCareComplaints", JSON.stringify(complaints)); }
function render(){
  document.querySelector("#totalCount").textContent = complaints.length;
  document.querySelector("#progressCount").textContent = complaints.filter(c => c.status === "In progress").length;
  document.querySelector("#resolvedCount").textContent = complaints.filter(c => c.status === "Resolved").length;
  const visible = currentFilter === "All" ? complaints : complaints.filter(c => c.status === currentFilter);
  const list = document.querySelector("#complaintList");
  list.innerHTML = visible.length ? visible.map(c => `<article class="complaint"><span class="issue-icon ${slug(c.category)}">${icons[c.category] || "!"}</span><div><h3>${escapeHtml(c.title)}</h3><p>${escapeHtml(c.location)} · ${c.id}</p></div><div class="status ${slug(c.status)}"><span>${c.status}</span><small>${c.date}</small></div></article>`).join("") : `<p style="padding:20px 0;color:#8795a0;font-size:13px">No complaints in this view.</p>`;
}
function escapeHtml(value){ return value.replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"})[char]); }
function toast(message){ const t=document.querySelector("#toast"); t.textContent=message; t.classList.add("show"); setTimeout(()=>t.classList.remove("show"),3200); }

document.querySelectorAll(".filter").forEach(button => button.addEventListener("click", () => { currentFilter=button.dataset.filter; document.querySelectorAll(".filter").forEach(b=>b.classList.toggle("active",b===button)); render(); }));
document.querySelector("#viewAll").addEventListener("click", () => { currentFilter="All"; document.querySelectorAll(".filter").forEach(b=>b.classList.toggle("active",b.dataset.filter==="All")); render(); document.querySelector("#complaints").scrollIntoView({behavior:"smooth"}); });
document.querySelector("#complaintForm").addEventListener("submit", event => { event.preventDefault(); const form = new FormData(event.target); const item={ id:`CC-${1043 + complaints.length}`, title:form.get("title"), category:form.get("category"), location:form.get("location"), priority:form.get("priority"), description:form.get("description"), status:"Open", date:"Just now" }; complaints.unshift(item); save(); render(); event.target.reset(); toast(`Complaint ${item.id} submitted successfully.`); document.querySelector("#complaints").scrollIntoView({behavior:"smooth",block:"start"}); });
render();
