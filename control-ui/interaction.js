"use strict";

const interactionActions = {
  pet: {name:"摸摸头", duration:2, expression:"happy"},
  poke: {name:"戳戳脸", duration:1.6, expression:"pout"},
  nod: {name:"点点头", duration:2, expression:"happy"},
  shake: {name:"摇摇头", duration:2.2, expression:"wink"},
  dance: {name:"坐姿小舞", duration:3.2, expression:"excited"},
  lift: {name:"提起晃晃", duration:2, expression:"worried"},
  feed: {name:"吃点心", duration:2.2, expression:"happy"},
  drink: {name:"喝口水", duration:2.2, expression:"happy"}
};
let interactionDirty = false, interactionSaving = false, careBusy = false;
let interactionBaseline = null, interactionError = "";
let previewSequence = 0, previewController, previewTimer, previewURL;
let lastPreview = null, previewSkin = null;
let feedReadyAt = 0, drinkReadyAt = 0;
const previewBlobs = new Map();
const reducedInteractionMotion = matchMedia("(prefers-reduced-motion: reduce)");

function interactionDraft() {
  const form = $("#interaction-form");
  return Object.fromEntries(["enabled", "touch_enabled", "effects_enabled"].map(key => [key, form.elements[key].checked]));
}
function interactionSettings(care) {
  return Object.fromEntries(["enabled", "touch_enabled", "effects_enabled"].map(key => [key, care[key]]));
}
function updateInteractionDirty() {
  interactionDirty = interactionBaseline !== null &&
    JSON.stringify(interactionDraft()) !== JSON.stringify(interactionBaseline);
}
function neutralPreview(expression="curious") {
  $("#interaction-preview").classList.add("preview-still");
  $("#interaction-preview").src = "/skin/" + (state?.settings.skin || "default") + "/" + expression + ".png";
  if (previewURL) { URL.revokeObjectURL(previewURL); previewURL = null; }
}
function cancelPreviewRequest() {
  previewSequence++;
  previewController?.abort(); previewController = null;
  clearTimeout(previewTimer);
  $(".interaction-stage").setAttribute("aria-busy", "false");
}
function stopInteractionPreview(message="预览已停止，可以再选一个动作") {
  cancelPreviewRequest();
  neutralPreview();
  $("#preview-pause").disabled = true;
  $("#preview-replay").disabled = !lastPreview;
  $("#interaction-preview-status").textContent = message;
  $(".interaction-stage").classList.remove("is-playing");
}
async function previewAnimation(action) {
  const info = interactionActions[action];
  if (!info || !state || $("#page-interaction").hidden || document.hidden) return;
  const stage = $(".interaction-stage"), box = stage.getBoundingClientRect();
  if (window.innerWidth <= 960 && (box.bottom < 140 || box.top > window.innerHeight - 140)) {
    stage.scrollIntoView({block:"start", behavior:"auto"});
  }
  // Leave the current pixels in place while fetching/decoding the next action.
  // Resetting to the PNG here produces two visible swaps on every click.
  cancelPreviewRequest();
  stage.setAttribute("aria-busy", "true");
  $("#interaction-preview-status").textContent = "正在准备“" + info.name + "”…";
  lastPreview = action;
  const sequence = previewSequence;
  $$("[data-preview]").forEach(item => item.setAttribute("aria-pressed", String(item.dataset.preview === action)));
  $("#preview-replay").disabled = false;
  $("#interaction-preview-detail").textContent = "只在面板内试映，不写入养成数值，也不向桌面排队。";
  if (reducedInteractionMotion.matches) {
    neutralPreview(info.expression);
    stage.setAttribute("aria-busy", "false");
    $("#interaction-preview-status").textContent = info.name + " · 静态表情";
    $("#interaction-preview-detail").textContent = "已遵循系统“减少动画”设置，仅显示动作表情。";
    return;
  }
  $("#preview-pause").disabled = false;
  const controller = new AbortController(); previewController = controller;
  const query = new URLSearchParams({skin:state.settings.skin,
    strength:$('input[name="preview_strength"]:checked').value,
    effects:interactionDraft().effects_enabled ? "1" : "0"});
  const key = action + "?" + query;
  let nextURL;
  try {
    let blob = previewBlobs.get(key);
    if (!blob) {
      const response = await fetch("/api/interaction-preview/" + action + ".webp?" + query,
        {headers:{"X-Nijika-Token":token}, signal:controller.signal});
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "动画暂时无法读取，请重试。");
      }
      blob = await response.blob();
      if (sequence !== previewSequence) return;
      if (previewBlobs.size >= 8) previewBlobs.delete(previewBlobs.keys().next().value);
      previewBlobs.set(key, blob);
    }
    if (sequence !== previewSequence || $("#page-interaction").hidden || document.hidden) return;
    nextURL = URL.createObjectURL(blob);
    const prepared = $("#interaction-preview").cloneNode(false);
    prepared.classList.remove("preview-still");
    prepared.src = nextURL;
    await prepared.decode();
    if (sequence !== previewSequence || $("#page-interaction").hidden || document.hidden) return;
    const previousURL = previewURL;
    $("#interaction-preview").replaceWith(prepared);
    previewURL = nextURL; nextURL = null;
    if (previousURL) URL.revokeObjectURL(previousURL);
    stage.setAttribute("aria-busy", "false");
    $("#interaction-preview-status").textContent = "正在试映：" + info.name;
    $(".interaction-stage").classList.add("is-playing");
    previewTimer = setTimeout(() => {
      if (sequence !== previewSequence) return;
      $("#interaction-preview-status").textContent = info.name + " · 播放完成";
      $("#preview-pause").disabled = true;
      $(".interaction-stage").classList.remove("is-playing");
    }, info.duration * 1000 + 600);
  } catch (error) {
    if (sequence !== previewSequence || error.name === "AbortError") return;
    $("#interaction-preview-status").textContent = "预览未播放：" + error.message;
    stage.classList.remove("is-playing");
    $("#preview-pause").disabled = !previewURL;
  } finally {
    if (nextURL) URL.revokeObjectURL(nextURL);
    if (sequence === previewSequence) {
      previewController = null;
      stage.setAttribute("aria-busy", "false");
    }
  }
}

function updateCareButtons() {
  const care = state?.interaction;
  const enabled = Boolean(care?.enabled) && !interactionDirty && !interactionSaving;
  const feedWait = Math.max(0, Math.ceil((feedReadyAt - Date.now()) / 1000));
  const drinkWait = Math.max(0, Math.ceil((drinkReadyAt - Date.now()) / 1000));
  $("#feed-pet").disabled = !enabled || careBusy || feedWait > 0;
  $("#water-pet").disabled = !enabled || careBusy || drinkWait > 0;
  $("#feed-pet").textContent = feedWait ? "点心 · " + feedWait + " 秒后" : "喂一块点心";
  $("#water-pet").textContent = drinkWait ? "喝水 · " + drinkWait + " 秒后" : "递一杯水";
  $("#care-help").textContent = interactionDirty ? "先保存下方互动设置，再来照顾她。"
    : enabled ? "点心加 20 饱食，喝水加 20 水分；每次也加 4 心情，最多 100。"
    : "在下方开启并保存养成，即可投喂；也可以先只看动画。";
  const form = $("#interaction-form");
  form.dataset.saveState = interactionError ? "error" : interactionSaving ? "saving"
    : interactionDirty ? "dirty" : "saved";
  form.setAttribute("aria-busy", String(interactionSaving));
  $("#save-interaction").disabled = interactionBaseline === null || !interactionDirty || interactionSaving;
  $("#interaction-save-status").textContent = interactionError ? "未能保存：" + interactionError
    : interactionSaving ? "正在保存，仍可继续修改…" : interactionDirty ? "有未保存的修改"
    : interactionBaseline === null ? "正在读取互动设置…" : "设置已保存在这台电脑";
  if (typeof updateDraftNotice === "function") updateDraftNotice();
}
function renderInteraction(care) {
  if (!care) return;
  const desktop = Boolean(state?.renderer?.desktop_playback);
  $("#interaction-desktop-status").textContent = desktop
    ? "桌面互动已连接：点击头顶、脸颊或身体，双击坐姿小舞；右键可选基础动作或停止。这里的动作按钮仅供试映，投喂会保存数值并发送桌面反馈。"
    : "桌面互动尚未连接，请先启动或更新虹夏桌宠。这里仍可试映动作、保存开关和照顾她；试映不会改变养成数值。";
  if (!interactionDirty && !interactionSaving) {
    const form = $("#interaction-form");
    for (const key of ["enabled", "touch_enabled", "effects_enabled"]) form.elements[key].checked = care[key];
    interactionBaseline = interactionSettings(care);
  }
  for (const key of ["satiety", "hydration", "mood"]) {
    $("#care-" + key).value = care[key];
    $("#care-" + key + "-text").textContent = Math.round(care[key]) + " / 100";
  }
  $("#care-state").textContent = care.enabled ? "养成进行中" : "养成未开启";
  $("#care-state").classList.toggle("enabled", care.enabled);
  $("#care-card").classList.toggle("care-disabled", !care.enabled);
  feedReadyAt = Date.now() + care.feed_wait * 1000;
  drinkReadyAt = Date.now() + care.drink_wait * 1000;
  updateCareButtons();
  if (previewSkin !== state.settings.skin) {
    previewSkin = state.settings.skin;
    previewBlobs.clear();
    stopInteractionPreview("选一个动作，看看她的回应");
    $("#interaction-preview-detail").textContent = previewSkin === "default"
      ? "双腿完整入画，动作结束会回到原来的坐姿。"
      : "当前使用自制皮肤；变形位置按默认坐姿，可能需要进一步适配。";
  }
}

$$("[data-preview]").forEach(item => item.addEventListener("click", () => previewAnimation(item.dataset.preview)));
$("#preview-replay").addEventListener("click", () => previewAnimation(lastPreview));
$("#preview-pause").addEventListener("click", () => stopInteractionPreview());
$("#interaction-character").addEventListener("click", event => {
  if (!interactionDraft().touch_enabled) {
    $("#interaction-preview-status").textContent = "分区触摸已关闭，仍可用左侧按钮试映";
    return;
  }
  const box = event.currentTarget.getBoundingClientRect();
  const x = (event.clientX - box.left) / box.width, y = (event.clientY - box.top) / box.height;
  const action = event.detail === 0 || y < .30 ? "pet" : y < .53 && x > .18 && x < .73 ? "poke" : "nod";
  previewAnimation(action);
});
$("#interaction-form").addEventListener("change", event => {
  interactionError = "";
  updateInteractionDirty();
  if (event.target.name === "effects_enabled") stopInteractionPreview("特效选项已更新，选个动作再试试");
  updateCareButtons();
});
$$('input[name="preview_strength"]').forEach(item => item.addEventListener("change", () => {
  stopInteractionPreview("试映幅度已更新，选个动作再试试");
}));
$("#interaction-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (interactionSaving || !interactionDirty) return;
  const draft = interactionDraft(); interactionSaving = true; interactionError = ""; updateCareButtons();
  try {
    const care = await api("/api/interaction", draft);
    interactionBaseline = interactionSettings(care);
    updateInteractionDirty();
    state.interaction = care; renderInteraction(care);
    toast("互动设置已保存。" + (state?.renderer?.desktop_playback ? "桌面会自动应用。" : "桌宠启动后应用。"));
  } catch (error) {
    interactionError = error.message || "请重试。";
    toast(interactionError, true);
  }
  finally { interactionSaving = false; updateCareButtons(); }
});
$$('[data-care]').forEach(item => item.addEventListener("click", async () => {
  if (careBusy) return;
  careBusy = true; updateCareButtons();
  try {
    const result = await api("/api/interaction", {action:item.dataset.care});
    state.interaction = result.care; renderInteraction(result.care);
    $("#care-result").textContent = result.action === "feed"
      ? "点心收到啦！饱食 +20、心情 +4，最多 100。"
      : "咕噜咕噜，喝到水啦！水分 +20、心情 +4，最多 100。";
    previewAnimation(result.action);
  } catch (error) { $("#care-result").textContent = error.message; toast(error.message, true); }
  finally { careBusy = false; updateCareButtons(); }
}));
document.addEventListener("nijika:page", event => {
  if (event.detail !== "interaction") stopInteractionPreview(lastPreview ? undefined : "选一个动作，看看她的回应");
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopInteractionPreview();
});
reducedInteractionMotion.addEventListener("change", () => stopInteractionPreview("系统动画偏好已更新"));
window.addEventListener("pagehide", () => { stopInteractionPreview(); previewBlobs.clear(); });
setInterval(updateCareButtons, 1000);
