
/* ============================================================
   Agent Prompt Builder
   ============================================================

   Moved out of Agentpromptbuilder.html so two hosts can run it: the
   standalone /prompt-builder page, and the right-hand panel on /test.
   The behaviour is the one the page always had - nothing below was
   rewritten for the move. What changed is the seam:

     - the four cards live here as MARKUP rather than in the page, so
       they are defined once instead of twice;
     - mount(host) replaces the init() that ran at parse, so importing
       this module has no side effects and the host decides when to
       start;
     - styles are builder.css, scoped under .pb.

   $() stays document.getElementById. That is only safe because the 26
   ids in MARKUP are unique against every host page's own ids; one
   builder instance per document. A second mount would share this
   module's state (categories, textCache, selection), so it is not
   supported. */

import API from '/static/js/api.js';

// ============================================================
// MARKUP
// ============================================================

const MARKUP = `
<div class="pb-cards">

  <div class="card">
    <h2>Parts Folder</h2>
    <div class="folderbar">
      <span>Parts:</span>
      <code id="parts_folder_label">…</code>
      <button id="refresh_parts_btn" class="secondary tiny" type="button" disabled title="Re-read the parts folder. Also clears any folder marked as locked after a failed write.">Refresh Parts</button>
    </div>
    <div id="storage_status" class="status">Connecting to the Project Manager…</div>
  </div>

  <div class="card">
    <h2 id="form_title">Create Prompt Part</h2>

    <label>Category</label>
    <div class="catrow">
      <select id="part_category"></select>
      <button id="new_category_btn" class="secondary tiny" type="button" disabled title="Add a category of your own. It becomes a new folder under prompt_parts.">+ Category</button>
      <button id="delete_category_btn" class="secondary tiny danger" type="button" disabled title="Delete the selected category and every part inside it.">Delete</button>
    </div>

    <div class="catrow" id="new_category_row" hidden>
      <input id="new_category_name" placeholder="new category name (e.g. memory)" maxlength="40" autocomplete="off">
      <button id="create_category_btn" class="secondary tiny" type="button" disabled>Create</button>
    </div>
    <div class="microlabel">the category list is stored in <code id="categories_file_label">categories.json</code> and is read on every refresh</div>

    <label>Name</label>
    <input id="part_name" placeholder="e.g. planner">

    <label>Text</label>
    <textarea id="part_text" placeholder="You are a planning agent..."></textarea>

    <div class="row">
      <button id="save_part_btn" type="button" disabled>Save Part</button>
      <button id="clear_form_btn" class="secondary" type="button" disabled>Clear</button>
    </div>

    <div id="part_status" class="status">Waiting for the Project Manager…</div>
  </div>

  <div class="card">
    <div class="headrow">
      <h2>Available Parts</h2>
      <button id="new_part_btn" class="secondary tiny" type="button" disabled>+ New Part</button>
    </div>
    <div id="parts_list"><div class="empty">Loading parts…</div></div>

    <div class="row">
      <button id="create_master_btn" type="button" disabled>Create Master Prompt</button>
    </div>
  </div>

  <div class="card">
    <h2>Master Prompt</h2>

    <label>Agent ID (folder name for saving)</label>
    <input id="agent_id" value="new_agent">

    <label>Markdown (editable before saving)</label>
    <textarea id="master_prompt" placeholder="Select parts and click 'Create Master Prompt'."></textarea>

    <div class="row">
      <button id="save_agent_btn" type="button" disabled>Save draft</button>
      <button id="publish_btn" type="button" disabled>Publish for testing</button>
      <button id="show_evidence_btn" class="secondary" type="button" disabled title="Select this agent on the dashboard and show its last run.">Show evidence</button>
    </div>

    <div id="master_status" class="status">Ready.</div>
  </div>

</div>`;

// ============================================================
// CONFIG - the storage locations are fixed, not user-selected.
// ============================================================

/* Every path is browser-root-qualified (workspace/..., test_environment/...),
   which is what the file API resolves back to a root. The prompt parts and the
   published test agents live in the isolated test environment, and the
   workspace root is the only other writable one, so the builder can only ever
   write inside those two - it can no longer be pointed at an arbitrary folder
   on the user's disk. */

const DOC_ROOT = 'test_environment/PromptBuilderFiles';
const PARTS_DIR = DOC_ROOT + '/prompt_parts';
const DOC_OUTPUT_DIR = DOC_ROOT + '/output/agents';
const AGENTS_DIR = 'test_environment/test_agents';

/* The category list is data, not code. It lives in this file next to the
   parts folders so it can be added to and subtracted from in the browser
   - and hand-edited - without touching this script. Array order is the
   order the dropdown, the parts list and the master prompt sections use,
   so there is no separate sort key to keep in sync. It sits outside
   prompt_parts/ so that folder holds nothing but category folders. */
const CATEGORIES_FILE = DOC_ROOT + '/categories.json';
const CATEGORIES_VERSION = 1;

const PART_FILE = '.txt';

/* The starting catalogue, written on the first run only. It is also the
   title lookup: a category typed as "hallucinations" gets the readable
   title from here rather than the id with a capital letter. */
const SEED_CATEGORIES = [
  { id: "role", title: "Role" },
  { id: "rules", title: "Rules" },
  { id: "hallucinations", title: "Hallucination Rules" },
  { id: "tools", title: "Tools" },
  { id: "skills", title: "Skills" },
  { id: "input", title: "Input" },
  { id: "reasoning", title: "Reasoning" },
  { id: "logic", title: "Logic" }
];

// ============================================================
// STATE
// ============================================================

let categories = [];           // [{id, title}] from the manifest, in order
let partIndex = {};            // {category: [{name, path}]}
let textCache = new Map();     // part path -> text
let selected = new Set();      // "category/name" keys that are checked
let lockedCategories = new Set(); // categories that refused a write
let editingCategory = null;    // category the part open in the form belongs to
let workspaceRoot = "";        // absolute, from /api/health
let projectRoot = "";          // the parent of workspaceRoot
let ready = false;             // the parts folder answered at least once
let assembled = null;          // selection signature of the last build

/* Every button the panel and the form can reach, so their disabled
   state is always derived from one place. */
const BUTTONS = ["save_part_btn","clear_form_btn","create_master_btn",
                  "save_agent_btn","publish_btn","refresh_parts_btn",
                  "new_part_btn","new_category_btn","create_category_btn",
                  "delete_category_btn","show_evidence_btn"];

/* Buttons that additionally need something published in this session,
   not just a live parts folder. "Show evidence" is the one that took
   the old test_btn's gate: it only has a verdict to point at once
   there is an agent for the dashboard to have tested. */
const PUBLISH_GATED = new Set(["show_evidence_btn"]);

let busy = false;

/* Document-wide on purpose. The ids are unique per document, so this is
   the same lookup the page always did and it costs nothing to keep -
   it also means MARKUP can be injected into a panel without rewriting
   every call site to take a root. */
function $(id){ return document.getElementById(id); }

function setStatus(id, message, kind){
  const el = $(id);
  el.textContent = message;
  el.className = "status" + (kind ? " " + kind : "");
}

/* One place decides every button's state, because three different
   things can disable one: the parts folder is unreachable, an operation
   is in flight, or there is nothing published to test. Deriving it in
   one pass is what keeps a later setReady() from quietly re-enabling a
   button whose own condition is gone. */
function syncButtons(){
  for (const id of BUTTONS){
    const gated = PUBLISH_GATED.has(id) && !publishedAgentId;
    $(id).disabled = busy || !ready || gated;
  }
}

function setReady(value){
  ready = value;
  syncButtons();
}

/* Buttons stay disabled for the duration of an operation so a double
   click cannot fire two writes at the same file. */
function setBusy(value){
  busy = value;
  syncButtons();
}

function partKey(category, name){ return category + "/" + name; }

function categoryPath(id){
  return PARTS_DIR + "/" + id;
}

function partPath(category, name){
  return categoryPath(category) + "/" + name + PART_FILE;
}

function relativePath(path){
  return path.startsWith(DOC_ROOT + "/")
    ? path.slice(DOC_ROOT.length + 1)
    : path;
}

function safeSlug(value){
  value = (value || "").trim().toLowerCase();
  value = value.replace(/[^a-z0-9_-]+/g, "_");
  value = value.replace(/_+/g, "_").replace(/^_|_$/g, "");
  if (!value) throw new Error("Name cannot be empty.");
  return value;
}

/* A category added in the browser has no entry in the seed, so its id is
   the title unless it is one of the seeded ones. */
function titleFor(id){
  const seeded = SEED_CATEGORIES.find(cat => cat.id === id);
  if (seeded) return seeded.title;
  return id.replace(/[_-]+/g, " ")
           .replace(/\b\w/g, c => c.toUpperCase());
}

/* agent.json needs a human label; derive one from the id rather than
   adding a field the builder would then have to keep in sync. */
function displayName(id){
  return id.replace(/[_-]+/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// ============================================================
// ERRORS - a raw Python errno is not an explanation
// ============================================================

/* The API reports the absolute server path, so a failure reads as
   "Permission denied: 'E:\agentCreator\project_manager\workspace\...'"
   - a path the user cannot click and does not recognise. Both roots are
   learned once so the same failure can be shown relative. Best effort:
   if the lookup fails the original text is still shown. */
function learnWorkspaceRoot(){
  if (typeof API.health !== "function") return Promise.resolve();
  return API.health()
    .then((data) => {
      workspaceRoot = (data && data.root) || "";
      projectRoot = workspaceRoot
        ? workspaceRoot.replace(/[\\/][^\\/]+[\\/]?$/, "")
        : "";
    })
    .catch(() => {
      workspaceRoot = "";
      projectRoot = "";
    });
}

function isPermissionError(error){
  const message = (error && error.message) || String(error);
  return /permission denied|access is denied|errno 13|winerror 5/i
    .test(message);
}

/* Python quotes the offending path: "... denied: 'C:\\...'". */
function extractFailedPath(message){
  const quoted = String(message).match(/'([^']+)'/);
  return quoted ? quoted[1] : "";
}

function shortenPath(value){
  let out = String(value || "");
  for (const root of [workspaceRoot, projectRoot]){
    if (!root) continue;
    out = out.split(root).join("");
  }
  return out.replace(/^[\\/]+/, "").replace(/\\/g, "/");
}

/* The remedy is the same for every refused write on the same volume, so
   it is named from the drive rather than hard-coded. Pass lowercase to
   embed it inside a sentence. */
function repairHint(lowercase){
  const drive = projectRoot.match(/^([A-Za-z]:)/);
  const target = drive ? drive[1] : "the drive";
  const text = "Repair the drive in an Administrator prompt: chkdsk "
    + target + " /f";
  return lowercase
    ? text.charAt(0).toLowerCase() + text.slice(1)
    : text;
}

function firstUnlockedCategory(){
  const free = categories.find(cat => !lockedCategories.has(cat.id));
  return free ? free.id : null;
}

/* A locked category is disabled in the dropdown rather than hidden, so
   it stays visible that it exists and is why it cannot be used. */
function syncCategoryDropdown(){
  const sel = $("part_category");
  if (!sel) return;
  for (const opt of sel.options){
    opt.disabled = lockedCategories.has(opt.value);
  }
  if (lockedCategories.has(sel.value)){
    const free = firstUnlockedCategory();
    if (free) sel.value = free;
  }
}

function markCategoryLocked(category){
  if (!category) return;
  lockedCategories.add(category);
  syncCategoryDropdown();
  renderParts();
}

/* Turns a thrown error into a sentence the user can act on, and records
   a refused folder so the panel stops offering it. */
function prettyError(error, category){
  const raw = (error && error.message) || String(error);

  if (isPermissionError(error)){
    if (category) markCategoryLocked(category);
    const where = shortenPath(
      extractFailedPath(raw) || "that folder"
    );
    return "Cannot write " + where
      + " - Windows reports \"access denied\". Nothing was saved."
      + " That folder is read-only or damaged: use another category, or "
      + repairHint(true) + ". Then press 'Refresh Parts'.";
  }

  return "Error: " + shortenPath(raw);
}

// ============================================================
// TREE LOOKUP - the /api/project tree is the listing source
// ============================================================

function findNode(items, path){
  for (const item of items || []){
    if (item.path === path) return item;
    if (item.children){
      const hit = findNode(item.children, path);
      if (hit) return hit;
    }
  }
  return null;
}

function childDir(node, name){
  for (const child of (node && node.children) || []){
    if (child.type === "directory" && child.name === name) return child;
  }
  return null;
}

// ============================================================
// FOLDER
// ============================================================

/* Only the parts root is created up front. Category folders appear on
   demand: every file write creates its parent directories, so seeding
   eight empty folders would just be eight pointless API calls - and a
   category with no parts does not need a folder to exist. */
async function ensureStructure(){
  await API.directoryCreate(PARTS_DIR);
  $("parts_folder_label").textContent = relativePath(PARTS_DIR);
  $("categories_file_label").textContent = relativePath(CATEGORIES_FILE);
}

// ============================================================
// CATEGORIES - the manifest is the list
// ============================================================

/* One entry per category, in the order everything else uses. A bad entry
   is dropped and a repeated id keeps its first position, because the
   manifest is a plain text file a person is allowed to edit. */
function normalizeCategories(raw){
  const list = Array.isArray(raw && raw.categories) ? raw.categories : [];
  const seen = new Set();
  const out = [];
  for (const item of list){
    if (!item || typeof item.id !== "string") continue;
    const id = item.id.trim().toLowerCase();
    if (!id || seen.has(id)) continue;
    const title = (typeof item.title === "string" && item.title.trim())
      || titleFor(id);
    seen.add(id);
    out.push({ id, title });
  }
  return out;
}

function manifestText(list){
  return JSON.stringify(
    { version: CATEGORIES_VERSION, categories: list }, null, 2
  ) + "\n";
}

/* Absent means "never set up", so the seed catalogue is written. Present
   but unreadable is an error and is never overwritten: a hand-edit with
   a typo in it has to survive until it is fixed. */
async function readCategories(){
  let text = null;

  try {
    text = (await API.fileRead(CATEGORIES_FILE)).content;
  } catch (error) {
    if (error.status !== 404) throw error;
  }

  if (text === null){
    const seeded = normalizeCategories({ categories: SEED_CATEGORIES });
    await API.fileWrite(CATEGORIES_FILE, manifestText(seeded));
    return seeded;
  }

  try {
    return normalizeCategories(JSON.parse(text));
  } catch (error) {
    throw new Error(relativePath(CATEGORIES_FILE)
      + " is not valid JSON (" + error.message + ")."
      + " Fix it in the editor - it has not been changed.");
  }
}

/* Every change goes through here, and the in-memory list is rebuilt from
   the same normalizer the file is written from, so what the page shows
   is always exactly what is on disk. */
async function writeCategories(list){
  const payload = normalizeCategories({ categories: list });
  await API.fileWrite(CATEGORIES_FILE, manifestText(payload));
  categories = payload;
  return payload;
}

// ============================================================
// PARTS
// ============================================================

function populateCategoryDropdown(){
  const sel = $("part_category");
  const previous = sel.value;
  sel.innerHTML = "";

  /* With every category deleted there is nothing to save a part into, and
     a blank dropdown would read as a bug rather than as that state. */
  if (!categories.length){
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "(no categories - create one)";
    sel.appendChild(none);
  }

  for (const cat of categories){
    const opt = document.createElement("option");
    opt.value = cat.id;
    opt.textContent = cat.title;
    sel.appendChild(opt);
  }

  /* A category that was just deleted is no longer an option, so the old
     value would quietly become the first one instead. */
  if (categories.some(cat => cat.id === previous)){
    sel.value = previous;
  }

  syncCategoryDropdown();
}

async function readPart(path){
  if (textCache.has(path)) return textCache.get(path);
  const data = await API.fileRead(path);
  const text = data.content || "";
  textCache.set(path, text);
  return text;
}

/* Selection is state, not DOM: the list is rebuilt from the tree on
   every refresh, so checked boxes are re-applied from `selected`
   instead of being inherited from the markup that just got replaced. */
async function refreshParts(){
  const data = await API.project();
  const partsNode = findNode(data.filesystem, PARTS_DIR);

  partIndex = {};
  for (const cat of categories){
    const catNode = childDir(partsNode, cat.id);
    const entries = [];
    for (const child of (catNode && catNode.children) || []){
      if (child.type !== "file") continue;
      if (!child.name.endsWith(PART_FILE)) continue;
      entries.push({ name: child.name.slice(0, -PART_FILE.length), path: child.path });
    }
    entries.sort((a, b) => a.name.localeCompare(b.name));
    partIndex[cat.id] = entries;
  }

  /* Drop selections whose part no longer exists, so a later build can
     never reference a file that was deleted or renamed. A category that
     was removed takes its checked parts with it. */
  const live = new Set();
  for (const cat of categories){
    for (const entry of partIndex[cat.id]) live.add(partKey(cat.id, entry.name));
  }
  const dropped = [];
  for (const key of Array.from(selected)){
    if (!live.has(key)){ selected.delete(key); dropped.push(key); }
  }

  renderParts();
  return { total: live.size, dropped };
}

function isChecked(category, name){
  return selected.has(partKey(category, name));
}

function setChecked(category, name, value){
  const key = partKey(category, name);
  if (value) selected.add(key); else selected.delete(key);
}

function markAssembledStale(){
  if (assembled === null) return;
  if (assembled === selectionSignature()) return;
  setStatus("master_status",
    "The selected parts changed. Click 'Create Master Prompt' to rebuild before saving.", "warn");
}

function selectionSignature(){
  return Array.from(selected).sort().join("|");
}

function renderParts(){
  const box = $("parts_list");
  box.innerHTML = "";

  let total = 0;

  for (const cat of categories){
    const id = cat.id;
    const entries = partIndex[id] || [];
    const locked = lockedCategories.has(id);
    total += entries.length;

    const group = document.createElement("div");
    group.className = "parts-group";

    const heading = document.createElement("h3");
    heading.appendChild(document.createTextNode(cat.title));
    heading.title = relativePath(categoryPath(id));

    const count = document.createElement("span");
    count.className = "count";
    count.textContent = "(" + entries.length + ")";
    heading.appendChild(count);

    /* The category is listed but cannot be used, so the panel says so
       instead of showing an empty list as if nothing had ever been
       written there. */
    if (locked){
      const badge = document.createElement("span");
      badge.className = "lockbadge";
      badge.textContent = "locked";
      badge.title = "This folder refused a write, so its parts cannot be"
        + " listed or saved. " + repairHint() + ", then press 'Refresh Parts'.";
      heading.appendChild(badge);
    }

    if (entries.length){
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "secondary tiny";
      toggle.textContent = "all / none";
      toggle.addEventListener("click", () => toggleCategory(id));
      heading.appendChild(toggle);
    }

    group.appendChild(heading);

    if (entries.length === 0){
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = locked
        ? "Folder is not writable right now."
        : "No parts yet.";
      group.appendChild(empty);
    }

    for (const entry of entries){
      group.appendChild(buildPartRow(id, entry));
    }

    box.appendChild(group);
  }

  if (total === 0){
    const hint = document.createElement("div");
    hint.className = "empty";
    hint.innerHTML =
      "No parts in the folder yet. Use \"+ New Part\" above, or add a"
      + " <code>.txt</code> file to <code>"
      + relativePath(PARTS_DIR) + "/&lt;category&gt;/</code> in the editor."
      + " A new category is a new folder there, so the editor works"
      + " without this page too.";
    box.appendChild(hint);
  }
}

function buildPartRow(category, entry){
  const row = document.createElement("div");
  row.className = "part-row";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = "part_" + category + "_" + entry.name;
  checkbox.checked = isChecked(category, entry.name);
  checkbox.addEventListener("change", () => {
    setChecked(category, entry.name, checkbox.checked);
    markAssembledStale();
  });

  const label = document.createElement("label");
  label.className = "name";
  label.htmlFor = checkbox.id;
  label.textContent = entry.name;
  label.title = entry.path;

  const actions = document.createElement("div");
  actions.className = "actions";

  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "secondary tiny";
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", () => editPart(category, entry));

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "secondary tiny";
  deleteBtn.textContent = "Delete";
  deleteBtn.addEventListener("click", () => deletePart(category, entry));

  actions.appendChild(editBtn);
  actions.appendChild(deleteBtn);
  row.appendChild(checkbox);
  row.appendChild(label);
  row.appendChild(actions);
  return row;
}

function toggleCategory(category){
  const entries = partIndex[category] || [];
  const allChecked = entries.length > 0
    && entries.every(entry => isChecked(category, entry.name));
  for (const entry of entries){
    setChecked(category, entry.name, !allChecked);
  }
  renderParts();
  markAssembledStale();
}

/* Clearing the fields and reporting "Ready" are separate: a successful
   save clears the form but must keep its own confirmation visible. */
function clearFormFields(){
  $("part_name").value = "";
  $("part_text").value = "";
  $("form_title").textContent = "Create Prompt Part";
  editingCategory = null;
}

function resetForm(){
  clearFormFields();
  setStatus("part_status", "Ready.");
}

function editPart(category, entry){
  setBusy(true);
  readPart(entry.path)
    .then((text) => {
      $("part_category").value = category;
      $("part_name").value = entry.name;
      $("part_text").value = text.replace(/\s+$/, "");
      $("form_title").textContent = "Edit Prompt Part";
      /* Remembered so deleting this category can say the open part goes
         with it, and so a cleared form is not mistaken for a live edit. */
      editingCategory = category;
      setStatus("part_status",
        "Editing " + relativePath(entry.path) + ". Save Part to update it.", "ok");
      $("part_text").focus();
    })
    .catch(error => setStatus("part_status", prettyError(error, category), "error"))
    .finally(() => setBusy(false));
}

function deletePart(category, entry){
  if (!confirm("Delete " + relativePath(entry.path) + "?")) return;
  setBusy(true);
  API.fileDelete(entry.path)
    .then(() => {
      textCache.delete(entry.path);
      selected.delete(partKey(category, entry.name));
      return refreshParts();
    })
    .then(({ total, dropped }) => {
      setStatus("part_status",
        "Deleted " + relativePath(entry.path) + ". " + total + " part(s) left."
        + droppedNote(dropped), "ok");
      markAssembledStale();
    })
    .catch(error => setStatus("part_status", prettyError(error, category), "error"))
    .finally(() => setBusy(false));
}

function droppedNote(dropped){
  if (!dropped.length) return "";
  return " Cleared " + dropped.length + " stale selection(s): " + dropped.join(", ") + ".";
}

// ============================================================
// CATEGORY ACTIONS
// ============================================================

/* The name field is hidden until it is asked for, so the form keeps one
   category selector instead of two near-identical text boxes. */
function toggleNewCategoryRow(open){
  const row = $("new_category_row");
  const show = open === undefined ? row.hidden : open;
  row.hidden = !show;
  $("new_category_btn").textContent = show ? "Cancel" : "+ Category";
  if (show) $("new_category_name").focus();
  else $("new_category_name").value = "";
}

/* Adding a category is a manifest write and nothing else: the folder is
   still created by the first part saved into it, which is the same
   "on demand" rule every other part follows. */
async function addCategory(){
  let id = "";
  try {
    id = safeSlug($("new_category_name").value);
  } catch (error) {
    setStatus("part_status", "Category " + error.message, "error");
    return;
  }

  if (categories.some(cat => cat.id === id)){
    setStatus("part_status",
      "The category '" + id + "' already exists.", "error");
    return;
  }

  setBusy(true);
  try {
    const title = titleFor(id);
    await writeCategories(categories.concat({ id, title }));
    toggleNewCategoryRow(false);
    populateCategoryDropdown();
    $("part_category").value = id;
    renderParts();
    setStatus("part_status", "Added category " + title + " -> "
      + relativePath(categoryPath(id))
      + ". Its folder appears with the first part saved into it.", "ok");
  } catch (error) {
    setStatus("part_status", prettyError(error), "error");
  } finally {
    setBusy(false);
  }
}

/* Everything the deleted folder was referenced by, so no path is left
   pointing at a folder that is gone. */
function forgetCategory(id){
  const prefix = categoryPath(id) + "/";
  for (const path of Array.from(textCache.keys())){
    if (path.startsWith(prefix)) textCache.delete(path);
  }
  for (const key of Array.from(selected)){
    if (key.startsWith(id + "/")) selected.delete(key);
  }
  lockedCategories.delete(id);
}

async function deleteCategory(){
  const id = $("part_category").value;
  const entry = categories.find(cat => cat.id === id);

  if (!entry){
    setStatus("part_status", "There is no category to delete.", "error");
    return;
  }

  const parts = partIndex[id] || [];
  const editing = editingCategory === id;

  /* One confirm says what is destroyed: the folder, every part in it,
     and an open part that otherwise would look like it survived. */
  let message = "Delete the category " + entry.title + " ("
    + relativePath(categoryPath(id)) + ")?";
  message += parts.length
    ? "\n\nThis permanently deletes " + parts.length + " part(s): "
      + parts.map(part => part.name).join(", ") + "."
    : "\n\nIt holds no parts.";
  if (editing){
    message += "\n\nThe part open in the form is one of them.";
  }
  if (!confirm(message)) return;

  setBusy(true);
  try {
    /* The folder goes first. A refused recursive delete then leaves the
       manifest untouched, so the list still matches the disk and the
       delete can simply be tried again - the other order would hide a
       category whose parts are already gone. A category that never had a
       part saved into it has no folder to remove, and a stale tree must
       not be able to skip a folder that does exist, so the answer to
       "is it there" comes from the delete itself. */
    try {
      await API.directoryDelete(categoryPath(id));
    } catch (error) {
      if (error.status !== 404) throw error;
    }
    forgetCategory(id);
    await writeCategories(categories.filter(cat => cat.id !== id));
    populateCategoryDropdown();

    const { total, dropped } = await refreshParts();
    if (editing) resetForm();
    setStatus("part_status", "Deleted category " + entry.title + ". "
      + total + " part(s) left." + droppedNote(dropped), "ok");
    markAssembledStale();
  } catch (error) {
    setStatus("part_status", prettyError(error, id), "error");
  } finally {
    setBusy(false);
  }
}

/* The create button in the panel header hands off to the form rather
   than duplicating it: two editors for one file is how the two drift
   apart. The category is moved off a locked folder first, because the
   first option is otherwise a folder that may refuse the write. */
function startNewPart(){
  if (!categories.length){
    setStatus("part_status",
      "There are no categories yet - use \"+ Category\" to add one first.", "warn");
    return;
  }
  const sel = $("part_category");
  if (lockedCategories.has(sel.value)){
    const free = firstUnlockedCategory();
    if (free) sel.value = free;
  }
  clearFormFields();
  const title = $("form_title");
  if (title && typeof title.scrollIntoView === "function"){
    title.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  $("part_name").focus();
  setStatus("part_status", "Fill in the form to create a new part.", "");
}

async function savePart(){
  const category = $("part_category").value;

  if (!category){
    setStatus("part_status",
      "There are no categories yet - use \"+ Category\" to add one first.", "error");
    return;
  }

  /* Refused up front: a locked folder already answered, so sending the
     write again would only repeat the same error. */
  if (lockedCategories.has(category)){
    setStatus("part_status",
      "Cannot save into " + titleFor(category) + " - that folder refused an"
      + " earlier write. " + repairHint() + ", then press 'Refresh Parts'.",
      "error");
    return;
  }

  setBusy(true);
  try {
    const name = safeSlug($("part_name").value);
    const text = $("part_text").value.trim();
    if (!text) throw new Error("Part text cannot be empty.");

    const path = partPath(category, name);
    /* fileWrite creates or overwrites, so saving an edited part and
       saving a new one are the same call. */
    await API.fileWrite(path, text + "\n");
    textCache.set(path, text + "\n");

    const { total } = await refreshParts();
    setStatus("part_status", "Saved: " + relativePath(path) + ". " + total + " part(s) total.", "ok");
    clearFormFields();
  } catch (error) {
    setStatus("part_status", prettyError(error, category), "error");
  } finally {
    setBusy(false);
  }
}

// ============================================================
// MASTER PROMPT
// ============================================================

function collectSelections(){
  const selections = {};
  for (const cat of categories){
    const names = (partIndex[cat.id] || [])
      .filter(entry => isChecked(cat.id, entry.name))
      .map(entry => entry.name);
    if (names.length) selections[cat.id] = names;
  }
  return selections;
}

async function buildMasterPrompt(){
  const selections = collectSelections();

  if (!Object.keys(selections).length){
    setStatus("master_status", "No parts are selected.", "warn");
    return;
  }

  setBusy(true);
  const missing = [];
  try {
    const lines = ["# Agent Prompt", ""];

    for (const cat of categories){
      const names = selections[cat.id] || [];
      const texts = [];
      for (const name of names){
        const path = partPath(cat.id, name);
        let text = "";
        try {
          text = (await readPart(path)).trim();
        } catch (error) {
          missing.push(partKey(cat.id, name));
          continue;
        }
        if (text) texts.push(text);
      }
      if (texts.length){
        lines.push("## " + cat.title);
        lines.push("");
        lines.push(texts.join("\n\n"));
        lines.push("");
      }
    }

    $("master_prompt").value = lines.join("\n").trim() + "\n";
    assembled = selectionSignature();

    const count = Object.values(selections).reduce((sum, list) => sum + list.length, 0);
    setStatus("master_status",
      "Assembled " + count + " part(s). Edit the markdown if needed, then save."
      + (missing.length ? " Skipped unreadable: " + missing.join(", ") + "." : ""),
      missing.length ? "warn" : "ok");
  } catch (error) {
    setStatus("master_status", "Error: " + error.message, "error");
  } finally {
    setBusy(false);
  }
}

function requireMarkdown(){
  const markdown = $("master_prompt").value.trim();
  if (!markdown) throw new Error("The master prompt is empty - nothing to save.");
  return markdown;
}

async function saveToDocumentation(){
  setBusy(true);
  try {
    const id = safeSlug($("agent_id").value);
    const markdown = requireMarkdown();
    const path = DOC_OUTPUT_DIR + "/" + id + "/agent.md";
    await API.fileWrite(path, markdown + "\n");
    setStatus("master_status", "Saved: " + relativePath(path), "ok");
  } catch (error) {
    setStatus("master_status", prettyError(error), "error");
  } finally {
    setBusy(false);
  }
}

/* "Publish for testing" makes the prompt a real agent inside the isolated
   test environment: the engine only lists folders that hold BOTH agent.json
   and agent.md (engine/agents/registry.py), so the metadata file is created
   here. An existing agent.json is left alone so hand-edited settings - and
   any tests stored in it - are never overwritten.

   Nothing is written to workspace/agents/. A published agent is a test
   fixture: it is not registered as an agent root, so it never appears in
   the live agent picker, and the four header tests drive it by path. */
let publishedAgentId = null;

async function publishForTesting(){
  setBusy(true);
  setPublished(false);
  try {
    const id = safeSlug($("agent_id").value);
    const markdown = requireMarkdown();
    const dir = AGENTS_DIR + "/" + id;

    await API.fileWrite(dir + "/agent.md", markdown + "\n");

    let metaCreated = false;
    try {
      await API.fileRead(dir + "/agent.json");
    } catch {
      const meta = {
        id,
        name: displayName(id),
        description: "",
        mode: "chat",
        model: "",
        tools: []
      };
      await API.fileCreate(dir + "/agent.json", JSON.stringify(meta, null, 2) + "\n");
      metaCreated = true;
    }

    setPublished(true);
    setStatus("master_status",
      "Published to the test environment: " + dir + "/agent.md"
      + (metaCreated ? " + agent.json (new)" : " (agent.json kept)")
      + ".\nRun it from the dashboard.", "ok");

    /* The host decides what publishing means for it: on /test this
       re-reads the agent list so the new agent is pickable. Hosts
       without a dashboard ignore it. */
    if (Builder.onPublished) Builder.onPublished(publishedAgentId);

  } catch (error) {
    setStatus("master_status", prettyError(error), "error");
  } finally {
    setBusy(false);
  }
}

/* "Show evidence" is only live for something that has actually been
   published in this session. Reloading the page forgets it, which is
   the honest state: a hand-edited agent.json may no longer match the
   markdown above, and the dashboard is where you find out.

   It hands the host the agent id rather than opening anything itself.
   The builder used to open the dashboard in a window from here; it now
   lives beside it, so one place runs the tests and one place shows the
   verdict, and the two cannot disagree. */
function setPublished(isPublished){
  publishedAgentId = isPublished ? publishedAgentId : safeSlug($("agent_id").value) || null;
  $("show_evidence_btn").title = publishedAgentId
    ? "Show the last run for " + publishedAgentId + " on the dashboard."
    : "Publish for testing first.";
  syncButtons();
}


// ============================================================
// RELOAD
// ============================================================

async function reloadParts(){
  setBusy(true);
  try {
    /* A lock only records that a write was refused, not that the folder
       is still broken, so the explicit refresh drops them and lets a
       repaired folder be used again without reloading the page. */
    lockedCategories.clear();
    syncCategoryDropdown();

    /* Read before the tree: the parts are listed per category, so the
       list has to be known first. A categories.json edited in the
       editor therefore takes effect on 'Refresh Parts'. */
    categories = await readCategories();
    populateCategoryDropdown();

    const { total, dropped } = await refreshParts();
    setStatus("storage_status",
      "Parts folder: " + relativePath(PARTS_DIR) + " - " + total + " part(s)."
      + droppedNote(dropped), "ok");
    setReady(true);
  } catch (error) {
    setReady(false);
    setStatus("storage_status", prettyError(error), "error");
  } finally {
    setBusy(false);
  }
}

// ============================================================
// MOUNT
// ============================================================

/* Was init(), which ran at parse because there was one host. The host
   now decides when the builder starts, which is what lets the same
   module back the standalone page and a panel. */
function mount(host){
  host.innerHTML = MARKUP;

  /* "Show evidence" starts live rather than gated: after a reload the
     publish is forgotten but the agent id is still in the box, and
     pointing the dashboard at it is harmless when there is nothing
     published - the dashboard's picker will simply not offer it. */
  setPublished(false);
  $("save_part_btn").addEventListener("click", savePart);
  $("clear_form_btn").addEventListener("click", resetForm);
  $("new_part_btn").addEventListener("click", startNewPart);
  $("new_category_btn").addEventListener("click", () => toggleNewCategoryRow());
  $("create_category_btn").addEventListener("click", addCategory);
  $("delete_category_btn").addEventListener("click", deleteCategory);
  $("new_category_name").addEventListener("keydown", (event) => {
    if (event.key === "Enter") addCategory();
  });
  $("create_master_btn").addEventListener("click", buildMasterPrompt);
  $("save_agent_btn").addEventListener("click", saveToDocumentation);
  $("publish_btn").addEventListener("click", publishForTesting);
  $("show_evidence_btn").addEventListener("click", () => {
    if (Builder.onShowEvidence) Builder.onShowEvidence(publishedAgentId);
  });
  $("refresh_parts_btn").addEventListener("click", reloadParts);

  /* The dropdown is not built here: it is a view of the manifest, and the
     manifest is read by the first reload. Every button is disabled until
     then, so the empty dropdown is never something a user can act on. */
  learnWorkspaceRoot()
    .then(() => ensureStructure())
    .then(() => reloadParts())
    .catch(error => {
      setReady(false);
      setStatus("storage_status", prettyError(error), "error");
      setStatus("part_status", "The parts folder is unavailable.", "error");
    });
}

const Builder = {
  mount,

  /* Both are host hooks rather than arguments because they are assigned
     before mount() runs in practice, and a host should not have to
     rebuild the panel to change what publishing does.

     onPublished(agentId)   - called after a successful publish.
     onShowEvidence(agentId) - the "Show evidence" button. Undefined on
     the standalone page, which has no dashboard to show. */
  onPublished: null,
  onShowEvidence: null,
};

export default Builder;

