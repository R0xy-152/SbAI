const form = document.querySelector("#player-form");
const input = document.querySelector("#player-message");
const dialogueText = document.querySelector("#dialogue-text");
const status = document.querySelector("#form-status");

function buildMockReply(message) {
  return `我听见了：“${message}”。这是 TV-01 的本地模拟回复。`;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();

  if (!message) {
    status.textContent = "请先输入一句话。";
    input.focus();
    return;
  }

  dialogueText.textContent = buildMockReply(message);
  status.textContent = "已发送；已显示本地模拟回复。";
  input.value = "";
  input.focus();
});
