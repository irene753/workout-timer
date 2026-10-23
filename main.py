"""FIT TIMER: PyScript 2026.7.3 - runs inside the browser."""
import math
from pyscript import document, window, when
from pyscript.ffi import create_proxy

work = 40
rest = 20
rounds = 5
round_no = 1
phase = "work"  # work, rest, done
running = False
remaining = float(work)
deadline = None


def el(element_id):
    return document.getElementById(element_id)


def render():
    secs = max(0, math.ceil(remaining))
    el("time-label").textContent = f"{secs // 60:02d}:{secs % 60:02d}"
    el("work-value").textContent = f"{work} 秒"
    el("rest-value").textContent = f"{rest} 秒"
    el("round-value").textContent = f"{rounds} 組"
    el("round-label").textContent = f"第 {round_no} / {rounds} 組"
    if phase == "done":
        title, hint, badge, button, color = "訓練完成 🎉", "做得很好！", "DONE", "再做一次", "#2bd3b3"
        fraction = 1.0
    else:
        title = "運動時間" if phase == "work" else "休息時間"
        hint = "持續加油！" if running and phase == "work" else "恢復呼吸" if running else "按下開始繼續"
        badge = "WORK" if running and phase == "work" else "REST" if running else "PAUSED"
        button = "暫停" if running else "開始 / 繼續"
        color = "#2bd3b3" if phase == "work" else "#ffc06a"
        duration = work if phase == "work" else rest
        fraction = max(0, min(1, (duration - remaining) / duration))
    el("phase-label").textContent = title
    el("phase-label").style.color = color
    el("hint").textContent = hint
    el("status-pill").textContent = badge
    el("start-btn").textContent = button
    el("progress-fill").style.width = f"{fraction * 100:.2f}%"
    el("progress-fill").style.backgroundColor = color
    el("ring").style.background = f"conic-gradient({color} {fraction * 100:.2f}%, #35455c 0%)"
    for name in ("work-minus", "work-plus", "rest-minus", "rest-plus", "round-minus", "round-plus"):
        el(name).disabled = running


def reset_state():
    global round_no, phase, running, remaining, deadline
    round_no, phase, running = 1, "work", False
    remaining, deadline = float(work), None
    render()


def advance_phase():
    global round_no, phase, running, remaining, deadline
    if phase == "work":
        if round_no == rounds:
            phase, running, remaining, deadline = "done", False, 0, None
            return
        phase, duration = "rest", rest
    else:
        round_no += 1
        phase, duration = "work", work
    remaining = float(duration)
    deadline += duration * 1000  # carry over elapsed time


def tick():
    global remaining
    if not running:
        return
    now = window.performance.now()
    while running and now >= deadline:
        advance_phase()
    if running:
        remaining = max(0, (deadline - now) / 1000)
    render()


@when("click", "#start-btn")
def toggle(event):
    global running, deadline, remaining
    if phase == "done":
        reset_state()
    if running:
        remaining = max(0, (deadline - window.performance.now()) / 1000)
        running, deadline = False, None
    else:
        running = True
        deadline = window.performance.now() + remaining * 1000
    render()


@when("click", "#reset-btn")
def reset(event):
    reset_state()


@when("click", ".stepper button")
def change(event):
    global work, rest, rounds
    if running:
        return
    name = str(event.currentTarget.id)
    step = 1 if name.endswith("plus") else -1
    if name.startswith("work"):
        work = max(5, min(3600, work + step * 5))
    elif name.startswith("rest"):
        rest = max(5, min(3600, rest + step * 5))
    else:
        rounds = max(1, min(100, rounds + step))
    reset_state()


reset_state()
el("start-btn").disabled = False
# Keep a strong reference to the callback proxy for JavaScript.
tick_proxy = create_proxy(tick)
interval_id = window.setInterval(tick_proxy, 100)
