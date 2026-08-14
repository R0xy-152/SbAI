const form = document.querySelector("#player-form");
const input = document.querySelector("#player-message");
const dialogueText = document.querySelector("#dialogue-text");
const status = document.querySelector("#form-status");
const characterSprite = document.querySelector("#character-sprite");
const sendButton = form.querySelector("button[type='submit']");

// TV-14: the session id is kept across a page refresh so the backend can
// restore the same game (Session Restore). localStorage is guarded because
// the Node DOM-stub tests have no browser storage.
function readSessionId() {
  if (typeof localStorage === "undefined") return null;
  try {
    return localStorage.getItem("gal_session_id") || null;
  } catch (_error) {
    return null;
  }
}

function writeSessionId(id) {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem("gal_session_id", id);
  } catch (_error) {
    // storage unavailable (e.g. private mode): the session still works for
    // this page load, it just does not survive a refresh.
  }
}

let sessionId = readSessionId();

// TV-03: when served by the FastAPI backend, use a same-origin /api/chat URL;
// when opened directly as a file, fall back to the local backend origin.
const API_BASE = (() => {
  if (
    typeof window !== "undefined" &&
    window.location &&
    window.location.protocol === "file:"
  ) {
    return "http://localhost:8000";
  }
  return "";
})();

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

async function sendMessage(message) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
  sessionId = data.session_id;
  writeSessionId(sessionId);
  return data;
}

function setWaiting(waiting) {
  input.disabled = waiting;
  sendButton.disabled = waiting;
  sendButton.textContent = waiting ? "思考中…" : "发送";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();

  if (!message) {
    status.textContent = "请先输入一句话。";
    input.focus();
    return;
  }

  const submitted = message;
  input.value = "";
  status.textContent = "已发送；正在等待角色回应…";
  setWaiting(true);

  try {
    const data = await sendMessage(submitted);
    dialogueText.textContent = data.dialogue;
    status.textContent = "已收到角色回应。";
  } catch (error) {
    status.textContent = "发送失败，请重试。";
    input.value = submitted; // restore the text so the player can retry
  } finally {
    setWaiting(false);
    input.focus();
  }
});
