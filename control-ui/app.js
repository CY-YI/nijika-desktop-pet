"use strict";
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const token = $('meta[name="nijika-token"]').content;
const clientNames = {codex:"Codex", work:"ChatGPT Work", dsh:"DeepSeek Harness",
  claude:"Claude Code", gemini:"Gemini CLI", copilot:"Copilot CLI", custom:"其他 MCP 客户端"};
const marks = {codex:"⌘", work:"✳", dsh:"≈", claude:"✷", gemini:"✧", copilot:"◎", custom:"＋"};
let state = null, toastTimer, refreshSequence = 0, refreshRequests = 0;
let agentsSignature = "", skinsSignature = "", supportSignature = "";
let skinPreviewSequence = 0;
let wizard = {step:1, client:"codex", plan:null, agent:null, busy:false};
const draftForms = [];
function bindDraft(id, status, page, label) {
  const draft = new FormDraft($(id), $(status), updateDraftNotice);
  draftForms.push({draft, page, label});
  return draft;
}
function updateDraftNotice() {
  const changed = draftForms.filter(item => item.draft.dirty || item.draft.saving);
  const interactionChanged = typeof interactionDirty !== "undefined" && interactionDirty;
  const labels = [...new Set(changed.map(item => item.label))];
  if (interactionChanged) labels.push("互动设置");
  $("#draft-notice").hidden = labels.length === 0;
  const message = "尚未保存 · " + labels.join("、") + "（切换页面会保留，关闭窗口前请保存）";
  if ($("#draft-summary").textContent !== message) $("#draft-summary").textContent = message;
  for (const item of $$(".nav-item")) {
    const dirty = changed.some(form => form.page === item.dataset.page) ||
      (interactionChanged && item.dataset.page === "interaction");
    item.classList.toggle("has-draft", dirty);
    item.setAttribute("aria-label", item.title + (dirty ? "，有未保存的修改" : ""));
  }
}
const settingsDraft = bindDraft("#settings-form", "#settings-status", "settings", "动作与陪伴");
const focusDraft = bindDraft("#focus-form", "#focus-save-status", "focus", "专注时长");
const reminderDraft = bindDraft("#reminder-form", "#reminder-status", "focus", "健康提醒");
const supportDraft = bindDraft("#support-form", "#support-save-status", "support", "投喂入口");
$("#review-drafts").addEventListener("click", () => {
  const target = draftForms.find(item => item.draft.dirty || item.draft.saving);
  const page = target?.page || "interaction";
  gotoPage(page);
  if (page === "support") $(".support-config").open = true;
  const form = target?.draft.form || $("#interaction-form");
  form.scrollIntoView({block:"center"});
  form.querySelector("input, select, textarea").focus({preventScroll:true});
});
window.addEventListener("beforeunload", event => {
  if (draftForms.some(item => item.draft.dirty || item.draft.saving) ||
      (typeof interactionDirty !== "undefined" && (interactionDirty || interactionSaving))) {
    event.preventDefault();
    event.returnValue = "";
  }
});

const SKIN_AI_PROMPT = [
"请制作可导入虹夏 Windows 桌宠的原创角色皮肤，优先交付含连续待机帧的 ZIP。只需小幅自然动作，不需要复杂转身。若无法制作多帧，请明确说明能力限制，再交付单张透明 PNG。",
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
"2. 画布比例：宽 : 高 ≈ 2 : 3，多帧统一使用 512×768 像素。",
"3. 图片四角必须是透明的，人物以外区域全部透明。",
"4. 总像素不超过 800 万，最小边不小于 32 像素。",
"5. 可选增加 9 张同角色、同尺寸、同位置的表情版本，只有表情不同，文件名分别是：",
"   curious.png（好奇/平静）、happy.png（开心微笑）、worried.png（担心求助）、sleepy.png（困倦）、",
"   wink.png（眨眼俏皮）、thinking.png（思考）、pout.png（小生气）、excited.png（兴奋加油）、blink.png（闭眼眨眼）。",
"   表情图可和下面的待机帧放在同一个 ZIP 中；只交付表情包时则仅放这 9 张图。",
"",
"【最后请告诉我】",
"1. 每张图的尺寸和格式；",
"2. 背景是否已经是真正的透明（请在导出后自检）；",
"3. 如果只能生成白色背景，请明确说明，我会自己抠图。",
"",
"【需要连续待机动画时，优先输出以下多帧 ZIP】",
"保持同一角色、同一画布和脚底位置，制作 2–48 张连续透明 PNG，建议 8–16 张、512×768。只做小幅呼吸、发梢摆动或眨眼，首尾衔接，不要改变脸型和衣服。",
"帧名依次为 idle_000.png、idle_001.png……；至少 2 张，所有帧必须同尺寸、宽高比约 2:3。",
'ZIP 根目录放 manifest.json，例如：{"name":"我的角色","idle":{"frames":["idle_000.png","idle_001.png"],"durations_ms":[120,120]}}。',
"请按实际帧数扩展 frames 和 durations_ms，数组长度一致。每帧 40–5000 毫秒、总长 ≤60 秒；输入 PNG 总像素 ≤2400 万，ZIP ≤32 MB、解压 ≤64 MB。建议 16 张 512×768。",
"八表情和 blink.png 可一起放入，且全部同尺寸；没有表情图时会以首帧补齐。除上述 PNG 和 manifest.json 外不要添加文件、脚本、说明或子 ZIP。",
"默认平静表情会循环播放待机；其他表情/互动暂时覆盖，结束后恢复。动作关闭时只显示静态图。若不能生成真实多帧或 ZIP，请如实说明，不要把同一张图复制多次冒充动画。"
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
async function downloadArchive(path, filename) {
  const response = await fetch(path, {headers:{"X-Nijika-Token":token}});
  if (!response.ok) throw new Error((await response.json()).error || "导出失败");
  download(await response.arrayBuffer(), filename, "application/zip");
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
  document.title = $("#page-name").textContent + " · 虹夏设置中心";
  document.dispatchEvent(new CustomEvent("nijika:page", {detail: page}));
  if (state) updateSkinPreview();
  $("#main-content").focus({preventScroll:true});
  window.scrollTo({top:0, behavior:"instant"});
}
$$(".nav-item").forEach(item => item.addEventListener("click", () => gotoPage(item.dataset.page)));
$(".brand").addEventListener("click", () => gotoPage("agents"));
$(".skip-link").addEventListener("click", event => {
  event.preventDefault();
  $("#main-content").focus();
});
window.addEventListener("hashchange", () => gotoPage(location.hash.slice(1)));

function testLabel(agent) {
  if (agent.host_activity?.answered) return "宿主调用 · 已点击";
  if (agent.host_activity?.called) return "收到宿主调用";
  if (agent.status === "managed" && !agent.test) return "MAGPIE 管理 · 待验证";
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
  const comparison = $("#agent-capabilities"); comparison.replaceChildren();
  for (const client of state.clients) {
    const info = client.capabilities;
    if (!info) continue;
    const row = node("article", "help-card");
    row.append(node("h3","",client.label),node("p","",info.transport),
      node("p","","完成：" + info.completion),node("p","","权限：" + info.approval),
      node("p","","生效：" + info.reload),node("small","",info.note));
    comparison.append(row);
  }
  for (const agent of state.agents) {
    const card = node("article","agent-card");
    const heading = node("div","agent-card-heading");
    heading.append(node("span","client-mark " + agent.client, marks[agent.client]));
    const title = node("div"); title.append(node("h3","",agent.name),node("small","",clientNames[agent.client]));
    heading.append(title,node("span","agent-status" + (agent.test?.status === "answered" ? " verified" : ""),testLabel(agent)));
    card.append(heading);
    const sourceEnv = agent.export?.mcpServers?.["nijika-pet"]?.env;
    if (sourceEnv) card.append(node("p","field-help","气泡来源：" +
      (/^VS Code(?: Insiders)?$/i.test(sourceEnv.NIJIKA_HOST_NAME || "") ?
        sourceEnv.NIJIKA_HOST_NAME + " · " + sourceEnv.NIJIKA_AGENT_NAME :
        sourceEnv.NIJIKA_AGENT_NAME + " · " + (sourceEnv.NIJIKA_HOST_NAME || "待补所在软件"))));
    card.append(node("p","field-help",agent.host_activity?.called ?
      "宿主调用已记录：" + agent.host_activity.agent + " · " + agent.host_activity.software +
      (agent.host_activity.answered ? "；该条桌面消息已点击。" : "；桌面回执尚未确认。") :
      "尚未收到带此档案编号的宿主调用。面板测试、旧配置或 MAGPIE 共享连接不能冒充此项验证。"));
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
let discovery = {items:[], selected:new Set(), batch:null, busy:false};
function discoveryControls() {
  $("#scan-agents").disabled = discovery.busy;
  $("#preview-discovery").disabled = discovery.busy || !discovery.selected.size;
  $("#apply-discovery").hidden = !discovery.batch;
  $("#apply-discovery").disabled = discovery.busy || !discovery.batch?.results.some(item => item.status === "ready");
  $$("#discovery-list input, #discovery-list button").forEach(item => item.disabled = discovery.busy);
}
function clearDiscoveryPlan() {
  discovery.batch = null;
  $("#discovery-results").replaceChildren();
  discoveryControls();
}
function renderDiscovery() {
  const list = $("#discovery-list"); list.replaceChildren();
  for (const item of discovery.items) {
    const card = node("article","discovery-item");
    const heading = node("label","discovery-heading");
    if (item.mode === "automatic") {
      const check = node("input"); check.type = "checkbox"; check.checked = discovery.selected.has(item.id);
      check.setAttribute("aria-label","选择 " + item.label);
      check.addEventListener("change", () => {
        if (check.checked) discovery.selected.add(item.id); else discovery.selected.delete(item.id);
        clearDiscoveryPlan();
      });
      heading.append(check);
    }
    heading.append(node("strong","",item.label),node("span","agent-status",item.status));
    card.append(heading,node("p","field-help",item.evidence.join("；") || "未找到已知入口，可通过单独向导指定目录。"),
      node("code","file-path",item.config_path),
      node("p","field-help",(item.manager === "magpie" ? "MAGPIE 管理；保留分发，不直接写配置。" : "") + item.verification));
    if (item.issue) card.append(node("p","form-error",item.issue));
    if (item.mode === "guided") {
      const guide = button(item.identity ? "接入此扩展" : "生成接入指引","button small secondary", () => {
        openWizard(); chooseClient("custom");
        const radio = $('#client-choices input[value="custom"]'); if (radio) radio.checked = true;
        $("#agent-name").value = item.identity || item.label;
        $("#agent-software").value = item.software;
        $("#agent-identity").value = item.identity || "Agent";
        $("#agent-location").value = item.location;
        renderWizard();
      });
      card.append(guide);
    }
    list.append(card);
  }
  discoveryControls();
}
async function discoveryAction(action) {
  if (discovery.busy) return;
  discovery.busy = true; discoveryControls();
  try {await action();}
  catch (error) {$("#scan-status").textContent = error.message;}
  finally {discovery.busy = false; discoveryControls();}
}
$("#scan-agents").addEventListener("click", () => discoveryAction(async () => {
  $("#scan-status").textContent = "正在检查已知入口…";
  const result = await api("/api/agents/scan",{});
  discovery.items = result.clients;
  clearDiscoveryPlan(); renderDiscovery();
  $("#scan-status").textContent = (result.scope ? result.scope + "。 " : "") + "扫描完成：" + result.clients.filter(item => item.detected).length +
    " 个入口有证据。请选择客户端；未发现的入口也可选择预览，缺依赖会单独提示。";
}));
$("#preview-discovery").addEventListener("click", () => discoveryAction(async () => {
  clearDiscoveryPlan();
  const result = await api("/api/agents/batch-plan",{clients:[...discovery.selected]});
  discovery.batch = result;
  const list = $("#discovery-results");
  list.append(node("p","field-help",result.note));
  for (const item of result.results) {
    const card = node("article","help-card");
    card.append(node("h3","",clientNames[item.client]));
    if (item.status !== "ready") card.append(node("p","form-error",item.error));
    else {
      card.append(...item.plan.notes.map(text => node("p","field-help",text)));
      for (const file of item.plan.files) card.append(node("p","field-help",file.action + " · " + file.purpose),
        node("code","file-path",file.path));
      if (!item.plan.files.length) card.append(node("p","field-help","不修改客户端文件，只保存管理档案及接入资料。"));
      if (item.plan.external_action) card.append(node("p","form-error","此项会调用 Codex CLI 注册 Work 本机插件；不授予信任或命令权限。"));
    }
    list.append(card);
  }
  $("#scan-status").textContent = "预览完成，尚未修改客户端。请查看各项路径、管理归属与外部操作后应用。";
}));
$("#apply-discovery").addEventListener("click", () => discoveryAction(async () => {
  const batchId = discovery.batch.batch_id;
  discovery.batch = null; discoveryControls();
  const result = await api("/api/agents/batch-apply",{batch_id:batchId});
  $("#discovery-results").replaceChildren(...result.results.map(item =>
    node("p",item.error ? "form-error" : "field-help",clientNames[item.client] + "：" +
      (item.error || (item.status === "managed" ? "保留 MAGPIE 管理，档案已保存。" :
        "配置已写入；" + item.backup_count + " 个文件已备份。重载客户端后验证调用。")))));
  $("#scan-status").textContent = "本轮处理结束，各客户端独立显示结果。下方伙伴卡片可查看步骤、复制验证提示词或做本机测试。";
  await refresh(true);
}));
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
  updateSkinPreview();
  $("#skin-preview-name").textContent = selected.name;
  $("#hero-character").src = "/skin/" + selected.id + "/curious.png";
  for (const skin of state.skins) {
    const active = skin.id === state.settings.skin;
    const card = node("article","skin-card" + (active ? " selected" : ""));
    const image = node("img"); image.src = "/skin/" + skin.id + "/curious.png"; image.alt = skin.name;
    card.append(image,node("h3","",skin.name),node("p","",skin.kind === "animated" ?
      "连续待机 · " + skin.idle.frames.length + " 帧" : skin.kind === "static" ? "单图皮肤 · 固定表情" : "九帧表情 · 支持眨眼"));
    if (active) card.append(node("span","skin-selected","正在使用"));
    const apply = button(active ? "已应用" : "应用这个外观","button " + (active ? "secondary" : "primary"),() => guarded(async () => {
      await api("/api/settings",{skin:skin.id}); await refresh(); toast("外观已保存，桌宠会自动应用。");
    },apply));
    apply.disabled = active; card.append(apply); list.append(card);
  }
}
async function updateSkinPreview() {
  const sequence = ++skinPreviewSequence;
  const skin = state.skins.find(item => item.id === state.settings.skin) || state.skins[0];
  const animate = skin.kind === "animated" && location.hash === "#skins" && !document.hidden &&
    state.settings.motion !== "off" && !matchMedia("(prefers-reduced-motion: reduce)").matches;
  const src = "/skin/" + skin.id + (animate ? "/idle.webp" : "/curious.png");
  const image = new Image(); image.src = src;
  try {
    await image.decode();
    if (sequence === skinPreviewSequence) {
      $("#skin-preview").src = src;
      $("#skin-preview-detail").textContent = animate ? "正在循环试映待机帧；桌面平静表情使用同一时序。" :
        skin.kind === "animated" ? "静态预览；进入衣橱并开启动作可查看多帧待机。" : "单图或九表情皮肤，保留原有连续动作。";
    }
  } catch {
    if (sequence === skinPreviewSequence) $("#skin-preview-detail").textContent = "预览未加载，请重新导入或切回默认皮肤。";
  }
}
document.addEventListener("visibilitychange", () => {if (state) updateSkinPreview();});
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
  supportDraft.sync(() => {
    for (const key of ["name","message","url"]) $("#support-form").elements[key].value = support[key];
  });
}

let focusSignature = "", notesSignature = "";
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
  focusDraft.sync(() => {
    form.elements.focus_minutes.value = timer.focus_minutes;
    form.elements.break_minutes.value = timer.break_minutes;
  }, "时长已保存在这台电脑");
  const reminders = data.reminders, paused = reminders.paused_until * 1000 > Date.now();
  reminderDraft.sync(() => {
    $("#reminder-enabled").checked = reminders.enabled;
    $("#sedentary-minutes").value = reminders.sedentary_minutes;
    $("#water-minutes").value = reminders.water_minutes;
    $("#eye-minutes").value = reminders.eye_minutes;
  }, !reminders.enabled ? "提醒已关闭"
    : paused ? "免打扰中，恢复后继续计时" : "提醒间隔已保存在本机");
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
  const sequence = ++refreshSequence;
  refreshRequests++;
  try {
    const nextState = await api("/api/state");
    if (sequence !== refreshSequence) return;
    state = nextState;
    const online = state.renderer.online;
    const pill = $("#renderer-pill"); pill.classList.toggle("online",online);
    pill.replaceChildren(node("i"),document.createTextNode(online ? "虹夏在桌面陪伴" : "桌宠尚未启动"));
    $("#start-pet").hidden = online; $("#pet-status").textContent = online ? "陪伴中" : "未启动";
    const nextAgents = JSON.stringify(state.agents);
    if (force || nextAgents !== agentsSignature) {agentsSignature = nextAgents; renderAgents();}
    const nextSkins = JSON.stringify([state.skins,state.settings.skin,state.settings.motion]);
    if (force || nextSkins !== skinsSignature) {skinsSignature = nextSkins; renderSkins(); previewMotion();}
    settingsDraft.sync(syncSettings, !online ? "已保存；桌宠启动后应用" :
      !state.renderer.supports_control ? "当前桌宠需更新后重启，才能应用面板设置" :
      state.renderer.applied_revision >= state.settings.revision ? "已同步到桌面上的虹夏" : "已保存，等待桌宠应用…");
    const nextSupport = JSON.stringify(state.support);
    if (force || nextSupport !== supportSignature) {supportSignature = nextSupport; renderSupport();}
    renderCompanion();
    if (typeof renderInteraction === "function") renderInteraction(state.interaction);
    updateDraftNotice();
    $("#connection-error").hidden = true;
  } catch (error) {
    if (sequence !== refreshSequence) return;
    $("#connection-error").textContent = "无法连接设置中心：" + error.message;
    $("#connection-error").hidden = false;
  } finally {
    refreshRequests--;
  }
}

function chooseClient(client) {
  wizard.client = client;
  $("#agent-name").value = clientNames[client];
  $("#agent-location").value = state.clients.find(item => item.id === client)?.location || "";
  $("#advanced-location").hidden = client === "custom";
  $("#custom-source").hidden = client !== "custom";
  $("#agent-software").required = client === "custom";
  $("#agent-software").disabled = client !== "custom";
  $("#agent-identity").disabled = client !== "custom";
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
  $$("#wizard-step-one input").forEach(input => {
    input.disabled = wizard.step !== 1 ||
      (["agent-identity","agent-software"].includes(input.id) && wizard.client !== "custom");
  });
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
  $("#agent-identity").value = "";
  $("#agent-software").value = "";
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
      wizard.plan = await api("/api/agents/plan",{client:wizard.client,name:$("#agent-name").value,location:$("#agent-location").value,
        agent_identity:wizard.client === "custom" ? $("#agent-identity").value.trim() || "Agent" : null,
        software:wizard.client === "custom" ? $("#agent-software").value.trim() : ""});
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

$("#settings-form").addEventListener("change", previewMotion);
$("#settings-form").addEventListener("submit",event => {
  event.preventDefault();
  guarded(async () => {
    const saved = await settingsDraft.save(draft => api("/api/settings",{...draft,width:Number(draft.width)}));
    if (saved) {await refresh(); toast(state.renderer.online ? "设置已保存，正在同步到虹夏。" : "设置已保存；启动桌宠后会自动应用。");}
  });
});
$("#import-skin").addEventListener("click",() => $("#skin-file").click());
$("#download-skin-template").addEventListener("click", event => guarded(
  () => downloadArchive("/api/skins/template","nijika-skin-template.zip"),event.currentTarget));
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
$("#support-form").addEventListener("submit",event => {
  event.preventDefault();
  guarded(async () => {
    const saved = await supportDraft.save(draft => api("/api/support",{name:draft.name.trim(),message:draft.message,url:draft.url.trim()}));
    if (saved) {await refresh(true); toast("投喂入口已保存。");}
  });
});
$("#upload-support").addEventListener("click",() => $("#support-file").click());
$("#export-support").addEventListener("click",event => guarded(async () => {
  if (supportDraft.dirty || supportDraft.saving) throw new Error("请先保存投喂入口，再导出公开资料。");
  await downloadArchive("/api/support/export","nijika-public-support.zip");
  toast("已导出公开赞助资料，仅包含说明、链接和收款图片。");
},event.currentTarget));
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
    const saved = await focusDraft.save(draft => api("/api/focus",{action:"configure",
      focus_minutes:Number(draft.focus_minutes),break_minutes:Number(draft.break_minutes)}));
    if (saved) {await refresh(true); toast("专注与休息时长已保存。");}
  });
});
$("#reminder-form").addEventListener("submit",event => {
  event.preventDefault();
  guarded(async () => {
    const saved = await reminderDraft.save(draft => api("/api/reminders",{enabled:draft["reminder-enabled"],
      sedentary_minutes:Number(draft["sedentary-minutes"]),water_minutes:Number(draft["water-minutes"]),
      eye_minutes:Number(draft["eye-minutes"])}));
    if (saved) {await refresh(true); toast("提醒设置已保存，间隔从此刻重新计算。");}
  });
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
setInterval(() => { if (!refreshRequests) refresh(); },3000);
