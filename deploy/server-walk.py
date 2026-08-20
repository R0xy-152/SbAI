# 服务器端完整剧本走查：advance/choose 直到 finished，打印统计。
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1"
player = "server-walk"


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


view = None
session = None
lines = 0
choices = 0
scene_changes = 0
picked = []
guard = 0
while True:
    guard += 1
    if guard > 5000:
        print("GUARD HIT"); break
    if view is None:
        view = post("/api/story/advance", {"session_id": session, "player_id": player})
    elif view["node"]["kind"] == "choice":
        choices += 1
        picked.append(view["node"]["choice_id"] + "=" + view["node"]["options"][0]["id"])
        view = post("/api/story/choose", {"session_id": session, "option_id": view["node"]["options"][0]["id"], "player_id": player})
        lines += 1
        continue
    elif view["finished"]:
        break
    else:
        view = post("/api/story/advance", {"session_id": session, "player_id": player})
        if view.get("scene_changed"):
            scene_changes += 1
        lines += 1
    session = view["session_id"]

print("finished:", view["finished"])
print("node_kind:", view["node"]["kind"])
print("lines:", lines, "choices:", choices, "scene_changes:", scene_changes)
print("picked:", picked)
# 刷新恢复 + 存档
with urllib.request.urlopen(BASE + "/api/story/current?session_id=" + session, timeout=30) as r:
    cur = json.loads(r.read().decode("utf-8"))
print("current after: started=%s finished=%s kind=%s" % (cur["started"], cur["finished"], cur["node"]["kind"]))
with urllib.request.urlopen(BASE + "/api/saves?player_id=" + player, timeout=30) as r:
    saves = json.loads(r.read().decode("utf-8"))
print("auto save exists:", saves.get("auto") is not None)
