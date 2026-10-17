"use strict";
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const token = $('meta[name="nijika-token"]').content;
const clientNames = {codex:"Codex", work:"ChatGPT Work", dsh:"DeepSeek Harness", custom:"其他 MCP 客户端"};
const marks = {codex:"⌘", work:"✳", dsh:"≈", custom:"＋"};
let state = null, settingsDirty = false, supportDirty = false, toastTimer;
let agentsSignature = "", skinsSignature = "", supportSignature = "";
let wizard = {step:1, client:"codex", plan:null, agent:null, busy:false};

const SKIN_AI_PROMPT = [
"请帮我制作一张可以用在 Windows 桌宠上的角色图。请先按下面的要求出图，成品请直接保存为 PNG 文件。",
"",
"【角色设定】（把下一行括号里的内容换成你想要的角色，例如“金发双马尾的动漫少女，绿色马甲，红色蝴蝶结，Q 版比例”）",
"（角色描述：）",
"",
"【画面要求】",
"1. Q 版可爱比例，全身入画，人物完整（头发、双手、双脚都不能被裁切）。",
"2. 姿态端正、正面朝向观众，人物水平居中，四周留出一点空白边距。",
"3. 人物占画面高度约 85%~90%，底部对齐，方便放在桌面上。",
"4. 线条干净、色彩明快，适合缩小到 320 像素宽时仍然看得清。",
"5. 背景必须完全透明（不是白色、不是棋盘格），除角色外不要任何装饰元素。",
"",
"【文件要求·非常重要，请严格遵守】",
"1. 格式：PNG，且必须带透明通道（RGBA）。",
"2. 画布比例：宽 : 高 ≈ 2 : 3，推荐尺寸 1024×1536 像素。",
"3. 图片四角必须是透明的，人物以外区域全部透明。",
"4. 总像素不超过 800 万，最小边不小于 32 像素。",
"5. 如果能一次输出多张，请再画 9 张同一个角色的表情版本，画布尺寸完全相同，只有表情不同，文件名分别是：",
"   curious.png（好奇/平静）、happy.png（开心微笑）、worried.png（担心求助）、sleepy.png（困倦）、",
"   wink.png（眨眼俏皮）、thinking.png（思考）、pout.png（小生气）、excited.png（兴奋加油）、blink.png（闭眼眨眼）。",
"   请把这 9 张打包成一个 ZIP，文件名与上面完全一致，不要改名、不要多加文件。",
"",
"【最后请告诉我】",
"1. 每张图的尺寸和格式；",
"2. 背景是否已经是真正的透明（请在导出后自检）；",
"3. 如果只能生成白色背景，请明确说明，我会自己抠图。"
].join("\n");

function renderSkinPrompt() {
  const box = $("#skin-prompt");
  if (box) box.textContent = SKIN_AI_PROMPT;
}

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
  if (!["agents","focus","notes","interaction","skins","settings","support"].includes(page)) page = "agents";
  $$(".page").forEach(item => item.hidden = item.id !== "page-" + page);
  $$(".nav-item").forEach(item => {
    item.classList.toggle("active", item.dataset.page === page);
    if (item.dataset.page === page) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  $("#page-name").textContent = {agents:"Agent 接入",focus:"专注与提醒",notes:"今日便签与陪伴",interaction:"互动与养成",skins:"角色衣橱",settings:"动作与陪伴",support:"投喂支持"}[page];
  history.replaceState(null,"", "#" + page);
  document.dispatchEvent(new CustomEvent("nijika:page", {detail: page}));
}
$$(".nav-item").forEach(item => item.addEventListener("click", () => gotoPage(item.dataset.page)));
$(".brand").addEventListener("click", () => gotoPage("agents"));

function testLabel(agent) {
  if (!agent.test) return agent.status === "exported" ? "接入资料就绪" : "已配置 · 待实测";
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
    const description = agent.status === "exported" ? "复制自动配置提示词给能操作本机的 AI，由它完成接入；文件保存在固定目录。" :
      agent.test?.status === "answered" ? "桌面显示与点击回传已验证。请在客户端新任务中确认 Agent 主动调用。" :
      "准备好后，先发一条桌面测试提醒；客户端需重启或新建任务后验证。";
    card.append(node("p","",description));
    const actions = node("div","agent-actions");
    const test = button(agent.test?.status === "pending" ? "等待桌面点击" : "测试提醒","button secondary", () => guarded(() => testAgent(agent.id),test));
    const guideButton = button("接入步骤","button secondary", () => guarded(() => openGuide(agent),guideButton));
    const exportButton = button("下载配置副本","button secondary", () => guarded(() => exportAgent(agent.id),exportButton));
    const remove = button("移除档案","remove-agent", () => guarded(async () => {
      await api("/api/agents/remove",{id:agent.id}); await refresh();
      toast("已移除面板档案，客户端配置保持不变。");
    },remove));
    actions.append(test,guideButton,exportButton,remove); card.append(actions); list.append(card);
  }
}
async function openGuide(agent) {
  agent = (await api("/api/agents/prepare",{id:agent.id})).agent;
  wizard = {step:3,client:agent.client,plan:{guide:agent.guide},agent,busy:false,guideOnly:true};
  $("#wizard-success-title").textContent = "接入 " + agent.name + " · 自动配置";
  $("#wizard-success-text").textContent = "接入文件已保存。复制提示词发给有本机操作能力的 AI，由它配置并验证。";
  $("#success-notes").replaceChildren();
  renderGuide(agent.guide, agent.needed_files, agent.bundle_directory);
  renderWizard();
  $("#agent-dialog").showModal();
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

let focusSignature = "", notesSignature = "", reminderDirty = false;
function renderCompanion() {
  const data = state.companion;
  if (!data) return;
  const timer = data.pomodoro;
  const running = timer.status === "running", breaking = timer.mode === "break";
  const ring = $("#focus-ring");
  ring.classList.toggle("running",running && !breaking);
  ring.classList.toggle("breaking",running && breaking);
  $("#focus-mode").textContent = timer.status === "idle" ? "准备开始" : timer.status === "paused" ? "已暂停" : breaking ? "休息中" : "专注中";
  $("#focus-clock").textContent = countdown(timer.remaining_seconds);
  $("#focus-hint").textContent = timer.status === "running"
    ? (breaking ? "喝完水、伸个懒腰再回来。" : "这一轮结束前，先专心做手上的事。")
    : timer.status === "paused" ? "点继续专注就会接着计时。" : "点下面的按钮开始第一轮";
  $("#focus-primary").textContent = running ? "暂停专注" : timer.status === "paused" ? "继续专注" : "开始专注";
  $("#focus-completed").textContent = timer.completed_today;
  $("#focus-minutes").textContent = Math.round((timer.focus_seconds_today || 0) / 60);
  $("#focus-streak").textContent = data.affection.days;
  const form = $("#focus-form");
  if (document.activeElement?.tagName !== "INPUT") {
    form.elements.focus_minutes.value = timer.focus_minutes;
    form.elements.break_minutes.value = timer.break_minutes;
  }
  const reminders = data.reminders, paused = reminders.paused_until * 1000 > Date.now();
  if (!reminderDirty) {
    $("#reminder-enabled").checked = reminders.enabled;
    $("#sedentary-minutes").value = reminders.sedentary_minutes;
    $("#water-minutes").value = reminders.water_minutes;
    $("#eye-minutes").value = reminders.eye_minutes;
  }
  $("#reminder-status").textContent = !reminders.enabled ? "提醒已关闭"
    : paused ? "免打扰中，恢复后继续计时" : "提醒间隔会保存在本机";
  $("#pause-reminders").hidden = paused;
  $("#resume-reminders").hidden = !paused;
  const signature = JSON.stringify(data.notes);
  if (signature !== notesSignature) { notesSignature = signature; renderNotes(); }
  const bond = data.affection, stage = bond.stage;
  $("#bond-stage").textContent = stage.name;
  $("#bond-line").textContent = stage.line;
  $("#bond-progress").style.width = Math.round(stage.progress * 100) + "%";
  $("#bond-days").textContent = bond.days;
  $("#bond-points").textContent = bond.points;
  $("#bond-interactions").textContent = bond.interactions;
  $("#bond-next").textContent = stage.next_at === null ? "已经是最亲密的阶段了，谢谢你一直在这里。"
    : "下一次亲密阶段会在 " + stage.next_at + " 点默契值。";
  focusSignature = JSON.stringify(timer);
}
function countdown(seconds) {
  seconds = Math.max(0,Math.round(seconds || 0));
  return String(Math.floor(seconds / 60)).padStart(2,"0") + ":" + String(seconds % 60).padStart(2,"0");
}
function renderNotes() {
  const list = $("#notes-list"), notes = state.companion.notes;
  list.replaceChildren();
  $("#notes-empty").hidden = notes.length !== 0;
  for (const note of notes) {
    const item = node("li"); item.classList.toggle("done",note.done);
    const label = node("label");
    const box = node("input"); box.type = "checkbox"; box.checked = note.done;
    box.addEventListener("change",() => guarded(async () => {
      await api("/api/notes",{action:"toggle",id:note.id}); await refresh(true);
    }));
    label.append(box,node("span",null,note.text));
    item.append(label,button("×","remove-note",() => guarded(async () => {
      await api("/api/notes",{action:"remove",id:note.id}); await refresh(true);
    })));
    list.append(item);
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
    renderCompanion();
    if (typeof renderInteraction === "function") renderInteraction(state.interaction);
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
function renderGuide(guide, neededFiles, bundleDirectory="") {
  if (!guide) return;
  $("#guide-title").textContent = guide.title;
  const steps = $("#guide-steps"); steps.replaceChildren();
  for (const text of guide.steps) steps.append(node("li", "", text));
  $("#guide-prompt").textContent = guide.prompt;
  $("#guide-tip").textContent = guide.tip;
  $("#bundle-location").textContent = bundleDirectory;
  wizard.neededFiles = neededFiles || [];
  renderNeededFiles(wizard.neededFiles);
}
function renderNeededFiles(files) {
  const list = $("#guide-files"); list.replaceChildren();
  for (const file of files || []) {
    const item = node("li");
    const head = node("div","file-head");
    head.append(node("span","file-kind " + (file.exists ? "ok" : "missing"), file.kind +
      (file.required ? "" : " · 可选") + (file.exists ? " · 已有" : file.required ? " · 待写入" : "")));
    head.append(node("span","file-label",file.label));
    item.append(head);
    const path = node("div","file-path-row");
    const code = node("code","file-path",file.path);
    path.append(code, button("复制","file-copy",() => guarded(() => copyText(file.path, null, "路径已复制"))));
    item.append(path);
    list.append(item);
  }
  $("#guide-files").dataset.empty = files && files.length ? "" : "1";
}
async function copyText(text, control, message="提示词已复制，可直接粘贴给 AI 客户端。") {
  try {
    await navigator.clipboard.writeText(text);
  } catch (error) {
    const area = node("textarea"); area.value = text;
    area.style.position = "fixed"; area.style.opacity = "0";
    ($("#agent-dialog").open ? $("#agent-dialog") : document.body).append(area); area.select();
    const copied = document.execCommand("copy"); area.remove();
    if (!copied) throw new Error("未能写入剪贴板，请手动选中下方提示词复制。");
  }
  if (control) {const label = control.textContent; control.textContent = "已复制 ✓"; setTimeout(() => control.textContent = label, 1800);}
  toast(message);
}
function renderWizard() {
  for (const step of [1,2,3]) $("#wizard-step-" + ["","one","two","three"][step]).hidden = wizard.step !== step;
  $$(".stepper li").forEach((item,index) => {item.classList.toggle("current",index+1 === wizard.step); item.classList.toggle("done",index+1 < wizard.step);});
  $("#wizard-back").textContent = wizard.step === 1 ? "取消" : wizard.step === 2 ? "← 上一步" : "完成";
  $("#wizard-next").textContent = wizard.step === 1 ? "检测并继续 →" : wizard.step === 2 ?
    wizard.client === "custom" ? "生成并保存接入文件" : "应用并添加" : wizard.guideOnly ? "复制自动配置提示词" :
    wizard.client === "custom" ? "复制自动配置提示词" : "发送测试提醒";
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
    const text = node("span"); text.append(node("strong","",client.label),node("small","",client.id === "custom" ? "复制提示词，让 AI 配置" : client.detected ? "检测到本机入口" : "选择后检查配置"));
    label.append(input,text); choices.append(label);
  }
  chooseClient("codex"); renderWizard(); $("#agent-dialog").showModal();
}
$$("[data-add-agent]").forEach(item => item.addEventListener("click",openWizard));
$("#close-wizard").addEventListener("click",() => $("#agent-dialog").close());
$("#copy-guide-prompt").addEventListener("click",() => guarded(() => copyText($("#guide-prompt").textContent,$("#copy-guide-prompt")),$("#copy-guide-prompt")));
$("#copy-guide-files").addEventListener("click",() => {
  const lines = (wizard.neededFiles || []).map(file => file.label + "\n" + file.path);
  guarded(() => copyText(lines.join("\n\n"), $("#copy-guide-files"), "已复制全部文件路径。"), $("#copy-guide-files"));
});
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
      if (!wizard.plan.files.length) $("#plan-files").append(node("li","field-help",wizard.client === "custom" ? "将自动保存接入文件到：" + wizard.plan.bundle_directory : "已有配置无需改动，将保存管理面板档案。"));
      $("#plan-notes").replaceChildren(...wizard.plan.notes.map(text => node("p","",text)));
      $("#plan-export").textContent = JSON.stringify(wizard.plan.export,null,2) + "\n\n" + wizard.plan.instructions;
      renderGuide(wizard.plan.guide, wizard.plan.needed_files, wizard.plan.bundle_directory);
      wizard.step = 2;
    } else if (wizard.step === 2) {
      const result = await api("/api/agents/apply",{plan_id:wizard.plan.plan_id}); wizard.agent = result.agent;
      $("#wizard-success-title").textContent = wizard.client === "custom" ? "配置已准备好" : "伙伴已添加";
      $("#wizard-success-text").textContent = wizard.client === "custom" ? "MCP 配置、规则和提示词已保存到下方目录，无需手动下载。复制提示词给 AI 即可开始自动配置。" :
        "已保存配置；" + (result.backup_count ? result.backup_count + " 个原文件已备份。" : "原有配置均已保留。");
      $("#success-notes").replaceChildren(...result.notes.map(text => node("p","",text)));
      renderGuide(result.agent.guide, result.agent.needed_files, result.agent.bundle_directory);
      wizard.step = 3; await refresh();
    } else {
      if (wizard.guideOnly) {
        await copyText($("#guide-prompt").textContent, $("#wizard-next"));
        wizard.busy = false; renderWizard(); return;
      } else if (wizard.client === "custom") {
        await copyText($("#guide-prompt").textContent, $("#wizard-next"));
        wizard.guideOnly = true;
        wizard.busy = false; renderWizard(); return;
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
$("#copy-skin-prompt").addEventListener("click",event => guarded(() => copyText(SKIN_AI_PROMPT,$("#copy-skin-prompt"),"提示词已复制，粘贴给会画图的 AI 即可。"),event.currentTarget));
$("#copy-skin-prompt-2").addEventListener("click",event => guarded(() => copyText(SKIN_AI_PROMPT,$("#copy-skin-prompt-2"),"提示词已复制，粘贴给会画图的 AI 即可。"),event.currentTarget));
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

$("#focus-primary").addEventListener("click",event => guarded(async () => {
  const timer = state.companion.pomodoro;
  const action = timer.status === "running" ? "pause" : timer.status === "paused" ? "resume" : "start";
  await api("/api/focus",{action});
  await refresh(true);
  toast(action === "start" ? "这一轮专注开始了。" : action === "pause" ? "已暂停，随时可以继续。" : "继续这一轮专注。");
},event.currentTarget));
$("#focus-reset").addEventListener("click",event => guarded(async () => {
  await api("/api/focus",{action:"reset"}); await refresh(true); toast("这一轮先结束了。");
},event.currentTarget));
$("#focus-form").addEventListener("submit",event => {
  event.preventDefault();
  guarded(async () => {
    await api("/api/focus",{action:"configure",focus_minutes:Number($("#focus-length").value),
      break_minutes:Number($("#break-length").value)});
    await refresh(true); toast("专注与休息时长已保存。");
  },event.currentTarget.querySelector('[type="submit"]'));
});
$("#reminder-form").addEventListener("input",() => reminderDirty = true);
$("#reminder-form").addEventListener("submit",event => {
  event.preventDefault();
  guarded(async () => {
    await api("/api/reminders",{enabled:$("#reminder-enabled").checked,
      sedentary_minutes:Number($("#sedentary-minutes").value),water_minutes:Number($("#water-minutes").value),
      eye_minutes:Number($("#eye-minutes").value)});
    reminderDirty = false; await refresh(true); toast("提醒设置已保存，间隔从此刻重新计算。");
  },event.currentTarget.querySelector('[type="submit"]'));
});
$("#pause-reminders").addEventListener("click",event => guarded(async () => {
  await api("/api/reminders",{pause_minutes:60}); await refresh(true); toast("好，接下来 60 分钟不打扰你。");
},event.currentTarget));
$("#resume-reminders").addEventListener("click",event => guarded(async () => {
  await api("/api/reminders",{pause_minutes:0}); await refresh(true); toast("提醒已恢复。");
},event.currentTarget));
$("#add-note").addEventListener("click",event => guarded(async () => {
  const input = $("#note-text"), text = input.value.trim();
  if (!text) throw new Error("先写点内容再添加。");
  if (state.companion.notes.length >= 20) throw new Error("今天的便签已经有 20 条了。");
  await api("/api/notes",{action:"add",text}); input.value = "";
  await refresh(true); toast("记下来了。");
},event.currentTarget));
$("#note-text").addEventListener("keydown",event => {
  if (event.key === "Enter") { event.preventDefault(); $("#add-note").click(); }
});
gotoPage(location.hash.slice(1));
renderSkinPrompt();
refresh();
setInterval(() => refresh(),3000);
