"use strict";
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const token = $('meta[name="nijika-token"]').content;
const clientNames = {codex:"Codex", work:"ChatGPT Work", dsh:"DeepSeek Harness", custom:"其他 MCP 客户端"};
const marks = {codex:"⌘", work:"✳", dsh:"≈", custom:"＋"};
let state = null, settingsDirty = false, supportDirty = false, toastTimer;
let agentsSignature = "", skinsSignature = "", supportSignature = "";
let wizard = {step:1, client:"codex", plan:null, agent:null, busy:false};

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = String(text);
  return item;
}
function button(text, classes, action) {
  const item = node("button", classes, text); item.type = "button";
  item.addEventListener("click", action); return item;
}
function toast(message, error=false) {
  const box = $("#toast"); box.textContent = message;
  box.className = error ? "toast error" : "toast"; box.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => box.hidden = true, 5000);
}
async function api(path, body, raw=false, filename="") {
  const headers = {"X-Nijika-Token":token};
  const options = {headers};
  if (body !== undefined) {
    options.method = "POST";
    options.body = raw ? body : JSON.stringify(body);
    headers["Content-Type"] = raw ? "application/octet-stream" : "application/json";
    if (filename) headers["X-Filename"] = encodeURIComponent(filename);
  }
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "操作未完成，请重试。");
  return payload;
}
async function guarded(action, control) {
  if (control) control.disabled = true;
  try { await action(); } catch (error) { toast(error.message, true); }
  finally { if (control) control.disabled = false; }
}
function download(data, filename, type="application/json") {
  const url = URL.createObjectURL(new Blob([data], {type}));
  const link = node("a"); link.href = url; link.download = filename;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
function gotoPage(page) {
  if (!["agents","skins","settings","support"].includes(page)) page = "agents";
  $$(".page").forEach(item => item.hidden = item.id !== "page-" + page);
  $$(".nav-item").forEach(item => {
    item.classList.toggle("active", item.dataset.page === page);
    if (item.dataset.page === page) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  $("#page-name").textContent = {agents:"Agent 接入",skins:"角色衣橱",settings:"动作与陪伴",support:"投喂支持"}[page];
  history.replaceState(null,"", "#" + page);
}
$$(".nav-item").forEach(item => item.addEventListener("click", () => gotoPage(item.dataset.page)));
$(".brand").addEventListener("click", () => gotoPage("agents"));

function testLabel(agent) {
  if (!agent.test) return agent.status === "exported" ? "待客户端导入" : "已配置 · 待实测";
  if (agent.test.status === "answered") return "本机测试已点击";
  if (agent.test.visible) return "测试正在显示";
  return {pending:"测试已排队",dismissed:"测试已关闭",expired:"测试已过期",not_found:"测试待重试"}[agent.test.status] || "等待测试";
}
function renderAgents() {
  const list = $("#agents-list"); list.replaceChildren();
  $("#empty-agents").hidden = state.agents.length !== 0;
  $("#agent-count").textContent = state.agents.length;
  $("#agent-badge").textContent = state.agents.length;
  $("#test-count").textContent = state.agents.filter(item => item.test?.status === "answered").length;
  for (const agent of state.agents) {
    const card = node("article","agent-card");
    const heading = node("div","agent-card-heading");
    heading.append(node("span","client-mark " + agent.client, marks[agent.client]));
    const title = node("div"); title.append(node("h3","",agent.name),node("small","",clientNames[agent.client]));
    heading.append(title,node("span","agent-status" + (agent.test?.status === "answered" ? " verified" : ""),testLabel(agent)));
    card.append(heading);
    const description = agent.status === "exported" ? "配置已生成，请在客户端导入，并加入主动提醒规则。" :
      agent.test?.status === "answered" ? "桌面显示与点击回传已验证。请在客户端新任务中确认 Agent 主动调用。" :
      "准备好后，先发一条桌面测试提醒；客户端需重启或新建任务后验证。";
    card.append(node("p","",description));
    const actions = node("div","agent-actions");
    const test = button(agent.test?.status === "pending" ? "等待桌面点击" : "测试提醒","button secondary", () => guarded(() => testAgent(agent.id),test));
    const exportButton = button("导出配置","button secondary", () => guarded(() => exportAgent(agent.id),exportButton));
    const remove = button("移除档案","remove-agent", () => guarded(async () => {
      await api("/api/agents/remove",{id:agent.id}); await refresh();
      toast("已移除面板档案，客户端配置保持不变。");
    },remove));
    actions.append(test,exportButton,remove); card.append(actions); list.append(card);
  }
}
async function testAgent(id) {
  const result = await api("/api/agents/test",{id}); await refresh();
  toast(result.status === "pending" ? "测试已进入队列。请留意桌面上的虹夏，点击后会在这里显示回执。" : "测试状态已更新。");
}
async function exportAgent(id) {
  const result = await api("/api/agents/export/" + id);
  download(JSON.stringify(result.config,null,2),"nijika-mcp.json");
  toast("MCP 配置已下载；主动提醒还需要客户端读取交互技能或触发规则。");
}
function renderSkins() {
  const list = $("#skins-list"); list.replaceChildren();
  $("#skin-count").textContent = state.skins.length + " 套外观";
  const selected = state.skins.find(item => item.id === state.settings.skin) || state.skins[0];
  $("#skin-preview").src = "/skin/" + selected.id + "/curious.png";
  $("#skin-preview-name").textContent = selected.name;
  $("#hero-character").src = "/skin/" + selected.id + "/curious.png";
  for (const skin of state.skins) {
    const active = skin.id === state.settings.skin;
    const card = node("article","skin-card" + (active ? " selected" : ""));
    const image = node("img"); image.src = "/skin/" + skin.id + "/curious.png"; image.alt = skin.name;
    card.append(image,node("h3","",skin.name),node("p","",skin.kind === "static" ? "单图皮肤 · 固定表情" : "九帧表情 · 支持眨眼"));
    if (active) card.append(node("span","skin-selected","正在使用"));
    const apply = button(active ? "已应用" : "应用这个外观","button " + (active ? "secondary" : "primary"),() => guarded(async () => {
      await api("/api/settings",{skin:skin.id}); await refresh(); toast("外观已保存，桌宠会自动应用。");
    },apply));
    apply.disabled = active; card.append(apply); list.append(card);
  }
}
function syncSettings() {
  const form = $("#settings-form");
  for (const key of ["motion","width","expression"]) form.elements.namedItem(key).value = state.settings[key];
  form.elements.chat_enabled.checked = state.settings.chat_enabled;
  previewMotion();
}
function previewMotion() {
  if (!state) return;
  const form = $("#settings-form"), image = $("#motion-preview");
  const sizes = {260:"small",320:"medium",380:"large"};
  image.className = "motion-" + form.elements.motion.value + " size-" + sizes[form.elements.width.value];
  image.src = "/skin/" + state.settings.skin + "/" + form.elements.expression.value + ".png";
}
function renderSupport() {
  const support = state.support;
  $("#support-message").textContent = support.message;
  $("#support-author").textContent = support.name;
  $("#support-unconfigured").hidden = Boolean(support.has_image || support.url);
  $("#support-image").hidden = !support.has_image;
  if (support.has_image) $("#support-image").src = "/support/qr.png?v=" + Date.now();
  const link = $("#support-link"); link.hidden = !support.url;
  if (support.url) link.href = support.url; else link.removeAttribute("href");
  if (!supportDirty) {
    for (const key of ["name","message","url"]) $("#support-form").elements[key].value = support[key];
  }
}
async function refresh(force=false) {
  try {
    state = await api("/api/state");
    const online = state.renderer.online;
    const pill = $("#renderer-pill"); pill.classList.toggle("online",online);
    pill.replaceChildren(node("i"),document.createTextNode(online ? "虹夏在桌面陪伴" : "桌宠尚未启动"));
    $("#start-pet").hidden = online; $("#pet-status").textContent = online ? "陪伴中" : "未启动";
    const nextAgents = JSON.stringify(state.agents);
    if (force || nextAgents !== agentsSignature) {agentsSignature = nextAgents; renderAgents();}
    const nextSkins = JSON.stringify([state.skins,state.settings.skin]);
    if (force || nextSkins !== skinsSignature) {skinsSignature = nextSkins; renderSkins(); previewMotion();}
    if (!settingsDirty) syncSettings();
    const nextSupport = JSON.stringify(state.support);
    if (force || nextSupport !== supportSignature) {supportSignature = nextSupport; renderSupport();}
    $("#settings-status").textContent = settingsDirty ? "有未保存的修改" : !online ? "已保存；桌宠启动后应用" :
      !state.renderer.supports_control ? "当前桌宠需更新后重启，才能应用面板设置" :
      state.renderer.applied_revision >= state.settings.revision ? "已同步到桌面上的虹夏" : "已保存，等待桌宠应用…";
    $("#connection-error").hidden = true;
  } catch (error) {
    $("#connection-error").textContent = "无法连接设置中心：" + error.message;
    $("#connection-error").hidden = false;
  }
}

function chooseClient(client) {
  wizard.client = client;
  $("#agent-name").value = clientNames[client];
  $("#agent-location").value = state.clients.find(item => item.id === client)?.location || "";
  $("#advanced-location").hidden = client === "custom";
}
function renderWizard() {
  for (const step of [1,2,3]) $("#wizard-step-" + ["","one","two","three"][step]).hidden = wizard.step !== step;
  $$(".stepper li").forEach((item,index) => {item.classList.toggle("current",index+1 === wizard.step); item.classList.toggle("done",index+1 < wizard.step);});
  $("#wizard-back").textContent = wizard.step === 1 ? "取消" : wizard.step === 2 ? "← 上一步" : "完成";
  $("#wizard-next").textContent = wizard.step === 1 ? "检测并继续 →" : wizard.step === 2 ?
    wizard.client === "custom" ? "保存配置档案" : "应用并添加" : wizard.client === "custom" ? "下载 MCP 配置" : "发送测试提醒";
  $("#wizard-next").disabled = wizard.busy; $("#wizard-back").disabled = wizard.busy; $("#close-wizard").disabled = wizard.busy;
  $("#wizard-error").hidden = true;
}
function openWizard() {
  if (!state) {toast("正在连接，请稍后再试。"); return;}
  wizard = {step:1,client:"codex",plan:null,agent:null,busy:false};
  const choices = $("#client-choices"); choices.replaceChildren();
  for (const client of state.clients) {
    const label = node("label","client-option");
    const input = node("input"); input.type = "radio"; input.name = "client"; input.value = client.id; input.checked = client.id === "codex";
    input.addEventListener("change",() => chooseClient(client.id));
    const text = node("span"); text.append(node("strong","",client.label),node("small","",client.id === "custom" ? "生成配置，手动导入" : client.detected ? "检测到本机入口" : "选择后检查配置"));
    label.append(input,text); choices.append(label);
  }
  chooseClient("codex"); renderWizard(); $("#agent-dialog").showModal();
}
$$("[data-add-agent]").forEach(item => item.addEventListener("click",openWizard));
$("#close-wizard").addEventListener("click",() => $("#agent-dialog").close());
$("#agent-dialog").addEventListener("cancel",event => {if (wizard.busy) event.preventDefault();});
$("#wizard-back").addEventListener("click",() => {
  if (wizard.step === 2) {wizard.step = 1; renderWizard();}
  else $("#agent-dialog").close();
});
$("#agent-form").addEventListener("submit",async event => {
  event.preventDefault(); if (wizard.busy) return;
  wizard.busy = true; renderWizard();
  try {
    if (wizard.step === 1) {
      wizard.plan = await api("/api/agents/plan",{client:wizard.client,name:$("#agent-name").value,location:$("#agent-location").value});
      $("#plan-files").replaceChildren();
      for (const file of wizard.plan.files) {
        const item = node("li"); item.append(node("strong","",file.action + " · " + file.purpose),node("code","",file.path)); $("#plan-files").append(item);
      }
      if (!wizard.plan.files.length) $("#plan-files").append(node("li","field-help",wizard.client === "custom" ? "生成通用 MCP 配置，不修改客户端文件。" : "已有配置无需改动，将保存管理面板档案。"));
      $("#plan-notes").replaceChildren(...wizard.plan.notes.map(text => node("p","",text)));
      $("#plan-export").textContent = JSON.stringify(wizard.plan.export,null,2) + "\n\n" + wizard.plan.instructions;
      wizard.step = 2;
    } else if (wizard.step === 2) {
      const result = await api("/api/agents/apply",{plan_id:wizard.plan.plan_id}); wizard.agent = result.agent;
      $("#wizard-success-title").textContent = wizard.client === "custom" ? "配置已准备好" : "伙伴已添加";
      $("#wizard-success-text").textContent = wizard.client === "custom" ? "下载 MCP 配置，并把触发说明加入客户端规则。" :
        "已保存配置；" + (result.backup_count ? result.backup_count + " 个原文件已备份。" : "原有配置均已保留。");
      $("#success-notes").replaceChildren(...result.notes.map(text => node("p","",text)));
      wizard.step = 3; await refresh();
    } else {
      if (wizard.client === "custom") {
        download(JSON.stringify(wizard.plan.export,null,2),"nijika-mcp.json");
        download(wizard.plan.instructions,"nijika-agent-instructions.txt","text/plain;charset=utf-8");
      } else await testAgent(wizard.agent.id);
      $("#agent-dialog").close();
    }
    wizard.busy = false; renderWizard();
  } catch (error) {
    wizard.busy = false; renderWizard(); $("#wizard-error").textContent = error.message; $("#wizard-error").hidden = false;
  }
});

$("#settings-form").addEventListener("change",() => {settingsDirty = true; previewMotion(); $("#settings-status").textContent = "有未保存的修改";});
$("#settings-form").addEventListener("submit",event => {
  event.preventDefault(); const form = event.currentTarget;
  guarded(async () => {
    await api("/api/settings",{motion:form.elements.motion.value,width:Number(form.elements.width.value),expression:form.elements.expression.value,chat_enabled:form.elements.chat_enabled.checked});
    settingsDirty = false; await refresh(); toast("设置已保存，正在同步到虹夏。");
  },form.querySelector('[type="submit"]'));
});
$("#import-skin").addEventListener("click",() => $("#skin-file").click());
$("#skin-file").addEventListener("change",event => {
  const file = event.target.files[0]; if (!file) return;
  guarded(async () => {
    if (file.size > 32*1024*1024) throw new Error("皮肤文件不能超过 32 MB。");
    const skin = await api("/api/skins/import",await file.arrayBuffer(),true,file.name);
    await refresh(); toast("已导入“" + skin.name + "”，选择应用即可切换。");
  },$("#import-skin")).finally(() => event.target.value = "");
});
$("#support-form").addEventListener("input",() => supportDirty = true);
$("#support-form").addEventListener("submit",event => {
  event.preventDefault(); const form = event.currentTarget;
  guarded(async () => {
    await api("/api/support",{name:form.elements.name.value.trim(),message:form.elements.message.value,url:form.elements.url.value.trim()});
    supportDirty = false; await refresh(true); toast("投喂入口已保存。");
  },form.querySelector('[type="submit"]'));
});
$("#upload-support").addEventListener("click",() => $("#support-file").click());
$("#support-file").addEventListener("change",event => {
  const file = event.target.files[0]; if (!file) return;
  guarded(async () => {
    if (file.size > 8*1024*1024) throw new Error("收款图片不能超过 8 MB。");
    await api("/api/support/image",await file.arrayBuffer(),true); await refresh(true); toast("收款展示图片已保存。");
  },$("#upload-support")).finally(() => event.target.value = "");
});
$("#start-pet").addEventListener("click",event => guarded(async () => {
  const result = await api("/api/pet/start",{}); toast(result.message); await refresh();
},event.currentTarget));
gotoPage(location.hash.slice(1));
refresh();
setInterval(() => refresh(),3000);
