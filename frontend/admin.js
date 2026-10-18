const API = "http://127.0.0.1:5000/api";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const form = $("hostelForm"), statusEl = $("status");
let editingId = null;

const keyInput = $("adminKey");
keyInput.value = sessionStorage.getItem("adminKey") || "";
keyInput.addEventListener("input", () => sessionStorage.setItem("adminKey", keyInput.value));

const say = (t, err = false) => { statusEl.textContent = t; statusEl.className = "status" + (err ? " error" : ""); };

async function api(path, method = "GET", body) {
  let res;
  try {
    res = await fetch(API + path, { method, headers: { "Content-Type": "application/json", "X-Admin-Key": keyInput.value },
      body: body ? JSON.stringify(body) : undefined });
  } catch { throw new Error("Cannot reach the server. Start it with: python app.py (inside the backend folder)."); }
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

// ---- room option rows
function roomRow(r = {}) {
  const d = document.createElement("div"); d.className = "roomrow";
  d.innerHTML = `
    <select data-f="sharing_capacity" aria-label="Sharing">${[1,2,3,4,5].map(n => `<option value="${n}" ${r.sharing_capacity == n ? "selected" : ""}>${n} sharing</option>`).join("")}</select>
    <select data-f="ac_type" aria-label="AC type"><option ${r.ac_type === "AC" ? "selected" : ""}>AC</option><option ${r.ac_type === "Non-AC" || !r.ac_type ? "selected" : ""}>Non-AC</option></select>
    <input data-f="monthly_rent" type="number" min="1" placeholder="Rent ₹" value="${r.monthly_rent ?? ""}" aria-label="Monthly rent">
    <input data-f="security_deposit" type="number" min="0" placeholder="Deposit ₹" value="${r.security_deposit ?? ""}" aria-label="Deposit">
    <input data-f="total_rooms" type="number" min="1" placeholder="Rooms" value="${r.total_rooms ?? ""}" aria-label="Total rooms">
    <input data-f="rooms_available" type="number" min="0" placeholder="Free" value="${r.rooms_available ?? ""}" aria-label="Rooms free">
    <label class="check"><input data-f="attached_bathroom" type="checkbox" ${r.attached_bathroom ? "checked" : ""}> Bathroom</label>
    <button type="button" class="plain" data-remove>Remove</button>`;
  $("rooms").appendChild(d);
}
$("addRoom").addEventListener("click", () => roomRow());
$("rooms").addEventListener("click", e => { if (e.target.dataset.remove !== undefined) e.target.closest(".roomrow").remove(); });

// ---- form <-> object
function readForm() {
  const f = new FormData(form), body = {};
  for (const [k, v] of f.entries()) if (String(v).trim() !== "") body[k] = String(v).trim();
  body.rooms = [...document.querySelectorAll(".roomrow")].map(row => {
    const r = {};
    row.querySelectorAll("[data-f]").forEach(el => {
      if (el.type === "checkbox") r[el.dataset.f] = el.checked ? 1 : 0;
      else if (el.value !== "") r[el.dataset.f] = el.value;
    });
    return r;
  });
  body.amenities = [...document.querySelectorAll("input[name=amenity]:checked")].map(b => b.value);
  return body;
}

function fillForm(h) {
  form.reset(); $("rooms").innerHTML = "";
  ["name","city","area","nearest_institution","gender_type","food_type","price_tier","rating","distance_to_campus_km","mess_price","laundry_price"]
    .forEach(k => { if (form.elements[k]) form.elements[k].value = h[k] ?? ""; });
  h.rooms.forEach(roomRow);
  document.querySelectorAll("input[name=amenity]").forEach(b => b.checked = h.amenities.includes(b.value));
}

function startNew() {
  editingId = null; form.reset(); $("rooms").innerHTML = ""; roomRow();
  document.querySelectorAll("input[name=amenity]").forEach(b => b.checked = false);
  $("formTitle").textContent = "New hostel"; $("saveBtn").textContent = "Create hostel";
}
$("newBtn").addEventListener("click", startNew);

form.addEventListener("submit", async e => {
  e.preventDefault();
  const body = readForm();
  try {
    const data = editingId ? await api(`/admin/hostels/${editingId}`, "PUT", body) : await api("/admin/hostels", "POST", body);
    say(`${data.message}: hostel ${data.hostel_id}.`);
    await loadList();
    await editHostel(data.hostel_id);
  } catch (err) { say(err.message, true); }
});

async function editHostel(id) {
  try {
    const h = await api(`/hostels/${id}`);
    editingId = id; fillForm(h);
    $("formTitle").textContent = `Edit hostel ${id}`; $("saveBtn").textContent = "Save changes";
    form.scrollIntoView({ behavior: "smooth" });
  } catch (err) { say(err.message, true); }
}

async function removeHostel(id, name) {
  if (!confirm(`Delete "${name}" and all its rooms? This cannot be undone.`)) return;
  try {
    const data = await api(`/admin/hostels/${id}`, "DELETE");
    say(`${data.message}: hostel ${id}.`);
    if (editingId === id) startNew();
    loadList();
  } catch (err) { say(err.message, true); }
}

// ---- list
async function loadList() {
  const city = $("cityFilter").value;
  try {
    const { hostels } = await api(`/hostels?limit=100${city ? "&city=" + encodeURIComponent(city) : ""}`);
    $("list").innerHTML = `<tr><th>ID</th><th>Name</th><th>City</th><th></th></tr>` + hostels.map(h =>
      `<tr><td>${h.hostel_id}</td><td>${esc(h.name)}</td><td>${esc(h.city)}</td>
       <td><button type="button" class="plain" data-edit="${h.hostel_id}">Edit</button>
           <button type="button" class="plain" data-del="${h.hostel_id}" data-name="${esc(h.name)}">Delete</button></td></tr>`).join("");
  } catch (err) { say(err.message, true); }
}
$("cityFilter").addEventListener("change", loadList);
$("list").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.edit) editHostel(Number(b.dataset.edit));
  if (b.dataset.del) removeHostel(Number(b.dataset.del), b.dataset.name);
});

// ---- start-up: cities and amenities
["Berhampur","Bengaluru","Bhubaneswar","Chennai","Cuttack","Delhi","Hyderabad","Jaipur","Kolkata","Kota","Pune"]
  .forEach(c => $("cityFilter").insertAdjacentHTML("beforeend", `<option>${c}</option>`));
fetch(`${API}/amenities`).then(r => r.json()).then(({ amenities }) => {
  $("amenityBox").innerHTML = amenities.map(a => `<label class="check"><input type="checkbox" name="amenity" value="${esc(a)}"> ${esc(a)}</label>`).join("");
}).catch(() => say("Cannot reach the server. Start it with: python app.py (inside the backend folder).", true));
startNew(); loadList();
