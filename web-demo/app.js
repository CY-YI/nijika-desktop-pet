const expressionNames = {
  curious: "好奇",
  happy: "开心",
  thinking: "思考",
  excited: "加油",
};

const petImage = document.querySelector("#demoPet");
const expressionLabel = document.querySelector("#expressionLabel");
const status = document.querySelector("#demoStatus");
const bubble = document.querySelector("#demoBubble");
const bubbleTitle = document.querySelector("#bubbleTitle");
const bubbleMessage = document.querySelector("#bubbleMessage");
const bubbleChoices = document.querySelector("#bubbleChoices");

function showBubble(title, message, choices = []) {
  bubbleTitle.textContent = title;
  bubbleMessage.textContent = message;
  bubbleChoices.replaceChildren();
  for (const choice of choices) {
    const button = document.createElement("button");
    button.className = "bubble-choice";
    button.type = "button";
    const content = document.createElement("span");
    content.className = "choice-content";
    const label = document.createElement("strong");
    label.textContent = choice.label;
    content.append(label);
    if (choice.description) {
      const description = document.createElement("small");
      description.textContent = choice.description;
      content.append(description);
    }
    button.append(content);
    if (choice.recommended) {
      const badge = document.createElement("span");
      badge.className = "choice-badge";
      badge.textContent = "推荐";
      button.append(badge);
    }
    button.addEventListener("click", () => {
      status.textContent = "你在演示中选择了「" + choice.label + "」。";
      showBubble("虹夏 · 已回复", "已选择「" + choice.label + "」，我会按这个方向继续。");
    });
    bubbleChoices.append(button);
  }
  bubble.classList.remove("is-hidden");
}

for (const button of document.querySelectorAll("[data-expression]")) {
  button.addEventListener("click", () => {
    const expression = button.dataset.expression;
    petImage.src = "../assets/sprites/" + expression + ".png";
    petImage.alt = "虹夏当前表情：" + expressionNames[expression];
    expressionLabel.textContent = "当前表情 · " + expressionNames[expression];
    for (const chip of document.querySelectorAll("[data-expression]")) {
      const active = chip === button;
      chip.classList.toggle("is-active", active);
      chip.setAttribute("aria-pressed", String(active));
    }
    status.textContent = "已切换为「" + expressionNames[expression] + "」表情。";
  });
}

document.querySelector("#completionButton").addEventListener("click", () => {
  status.textContent = "完成提醒已在网页预览中显示。";
  showBubble("Codex · 页面已完成", "页面制作完成啦，来看看实际效果吧。", [
    { label: "知道了" },
  ]);
});

document.querySelector("#decisionButton").addEventListener("click", () => {
  status.textContent = "选择题已在网页预览中显示。";
  showBubble("Codex · 需要你选择", "下一步先完善哪个部分？", [
    { label: "先做界面", description: "先验证视觉和交互，更快看到结果。", recommended: true },
    { label: "先做连接", description: "先验证消息来源，再完善页面。" },
  ]);
});

document.querySelector("#closeBubble").addEventListener("click", () => {
  bubble.classList.add("is-hidden");
  status.textContent = "气泡已关闭，可以再次模拟提醒。";
});
