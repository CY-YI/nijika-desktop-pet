const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function harness() {
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../control-ui/form-state.js"), "utf8") +
    "\nthis.FormDraft = FormDraft;", context);
  const field = {name:"minutes", tagName:"INPUT", type:"number", value:"25"};
  const submit = {}, status = {textContent:"Saved"}, handlers = {};
  const form = {elements:[field], dataset:{}, setAttribute() {},
    querySelector:() => submit, addEventListener:(name, callback) => handlers[name] = callback};
  const draft = new context.FormDraft(form, status);
  return {draft, field, submit, status, form,
    edit(value) { field.value = value; handlers.input(); }};
}
function pending() {
  let resolve;
  const promise = new Promise(done => resolve = done);
  return {promise, resolve};
}

test("unloaded forms cannot save; reverting to saved values clears the draft", () => {
  const h = harness();
  assert.equal(h.submit.disabled, true);
  h.draft.sync(() => {});
  h.edit("37");
  assert.equal(h.draft.dirty, true);
  assert.equal(h.submit.disabled, false);
  h.edit("25");
  assert.equal(h.draft.dirty, false);
  assert.equal(h.submit.disabled, true);
});

test("polling cannot overwrite a draft after the field loses focus", () => {
  const h = harness();
  h.draft.sync(() => {});
  h.edit("37");
  h.draft.sync(() => h.field.value = "25");
  assert.equal(h.field.value, "37");
});

test("new edits survive a save and a subsequent server refresh", async () => {
  const h = harness(), saved = pending();
  h.draft.sync(() => {});
  h.edit("37");
  let sent;
  const save = h.draft.save(value => {sent = value.minutes; return saved.promise;});
  assert.equal(h.submit.disabled, true);
  h.edit("42");
  h.draft.sync(() => h.field.value = "25");
  assert.equal(h.field.value, "42");
  saved.resolve();
  await save;
  h.draft.sync(() => h.field.value = "37");
  assert.equal(sent, "37");
  assert.equal(h.field.value, "42");
  assert.equal(h.draft.dirty, true);
  assert.equal(h.submit.disabled, false);
});

test("a save cannot be sent twice, even if the user submits again", async () => {
  const h = harness(), saved = pending();
  h.draft.sync(() => {});
  h.edit("37");
  let calls = 0;
  const first = h.draft.save(() => {calls++; return saved.promise;});
  assert.equal(await h.draft.save(() => {calls++;}), false);
  saved.resolve(); await first;
  assert.equal(calls, 1);
  assert.equal(h.draft.dirty, false);
});

test("failed saves keep the draft and persistent error until edited or retried", async () => {
  const h = harness();
  h.draft.sync(() => {});
  h.edit("37");
  await assert.rejects(h.draft.save(() => {throw new Error("Offline");}), /Offline/);
  h.draft.sync(() => h.field.value = "25");
  assert.equal(h.field.value, "37");
  assert.match(h.status.textContent, /Offline/);
  assert.equal(h.submit.disabled, false);
  assert.equal(h.form.dataset.saveState, "error");
  await h.draft.save(async () => {});
  assert.equal(h.form.dataset.saveState, "saved");
});

test("a clean-looking form is still protected from polling during an active save", async () => {
  const h = harness(), saved = pending();
  h.draft.sync(() => {});
  h.edit("37");
  const save = h.draft.save(() => saved.promise);
  h.edit("25");
  h.draft.sync(() => h.field.value = "99");
  assert.equal(h.field.value, "25");
  saved.resolve(); await save;
  assert.equal(h.draft.dirty, true);
});

test("checkboxes, radio groups and selects produce the values of the submitted draft", async () => {
  const h = harness();
  h.form.elements.push(
    {id:"enabled",tagName:"INPUT",type:"checkbox",checked:false},
    {name:"motion",tagName:"INPUT",type:"radio",value:"off",checked:true},
    {name:"motion",tagName:"INPUT",type:"radio",value:"gentle",checked:false},
    {name:"expression",tagName:"SELECT",type:"select-one",value:"happy"},
    {id:"upload",tagName:"INPUT",type:"file",value:"ignored.png"}
  );
  h.draft.sync(() => {});
  h.form.elements[1].checked = true;
  h.form.elements[2].checked = false;
  h.form.elements[3].checked = true;
  let sent;
  await h.draft.save(async value => sent = value);
  assert.deepEqual(JSON.parse(JSON.stringify(sent)),
    {minutes:"25",enabled:true,motion:"gentle",expression:"happy"});
});
