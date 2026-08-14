const form = document.querySelector("#player-form");
const input = document.querySelector("#player-message");
const dialogueText = document.querySelector("#dialogue-text");
const status = document.querySelector("#form-status");
const characterSprite = document.querySelector("#character-sprite");

const animationClasses = {
  fade_in: "is-fading-in",
  fade_out: "is-fading-out",
  shake: "is-shaking",
};

const expressionNames = new Set(["normal", "alert"]);

function replayAnimation(className, afterAnimation) {
  characterSprite.classList.remove(className);
  void characterSprite.offsetWidth;
  characterSprite.classList.add(className);
  characterSprite.addEventListener(
    "animationend",
    () => {
      characterSprite.classList.remove(className);
      afterAnimation?.();
    },
    { once: true },
  );
}

function applyPresentationDirective({ character, animation, expression } = {}) {
  if (character !== characterSprite.dataset.character) {
    return { applied: false, reason: "unknown_character" };
  }

  if (expression !== undefined) {
    if (!expressionNames.has(expression)) {
      return { applied: false, reason: "unknown_expression" };
    }
    characterSprite.dataset.expression = expression;
  }

  if (animation !== undefined) {
    const animationClass = animationClasses[animation];
    if (!animationClass) {
      return { applied: false, reason: "unknown_animation" };
    }

    if (animation === "fade_in") {
      characterSprite.classList.remove("is-hidden");
    }
    replayAnimation(animationClass, () => {
      if (animation === "fade_out") {
        characterSprite.classList.add("is-hidden");
      }
    });
  }

  return { applied: true };
}

if (typeof window !== "undefined") {
  window.galPresentation = { apply: applyPresentationDirective };
}

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


