
import math
from pyscript import document, window, when
from pyscript.ffi import create_proxy

# ===== 預設設定 =====
prep = 10
work = 40
rest = 20
rounds = 5

# ===== 計時狀態 =====
round_no = 1
phase = "prep"
running = False
started = False
remaining = float(prep)
deadline = None
last_countdown = None

current_utterance = None


def el(name):
    return document.getElementById(name)


# ===== 英文語音 =====
def speak(message):
    global current_utterance

    synth = window.speechSynthesis
    synth.cancel()

    utterance = window.SpeechSynthesisUtterance.new(message)
    utterance.lang = "en-US"
    utterance.rate = 1.1
    utterance.pitch = 1.0
    utterance.volume = 1.0

    voices = synth.getVoices()

    # 優先選擇美式英文
    for voice in voices:
        if str(voice.lang).lower() == "en-us":
            utterance.voice = voice
            break
    else:
        for voice in voices:
            if str(voice.lang).lower().startswith("en"):
                utterance.voice = voice
                break

    current_utterance = utterance
    synth.speak(utterance)


def duration_of(p):
    return {
        "prep": prep,
        "work": work,
        "rest": rest
    }.get(p, 1)


# ===== 更新畫面 =====
def render():
    seconds = max(0, math.ceil(remaining))

    el("time-label").textContent = (
        f"{seconds // 60:02d}:{seconds % 60:02d}"
    )

    settings = [
        ("prep", prep, "秒"),
        ("work", work, "秒"),
        ("rest", rest, "秒"),
        ("round", rounds, "組")
    ]

    for name, value, unit in settings:
        el(f"{name}-value").textContent = f"{value} {unit}"

    el("round-label").textContent = (
        f"第 {round_no} / {rounds} 組"
    )

    titles = {
        "prep": "預備時間",
        "work": "運動時間",
        "rest": "休息時間",
        "done": "運動完成 🎉"
    }

    colors = {
        "prep": "#82b4ff",
        "work": "#008f7a",
        "rest": "#ffc06a",
        "done": "#2bd3b3"
    }

    color = colors[phase]

    # ===== 運動階段切換白色背景 =====
    document.body.classList.toggle(
        "work-mode", phase == "work"
    )

    if phase == "done":
        hint = "做得很好！"
        badge = "DONE"
        button = "再做一次"
        fraction = 1.0

    else:
        hints = {
            "prep": "準備開始運動！",
            "work": "持續加油！",
            "rest": "休息一下，準備下一組！"
        }

        if running:
            hint = hints[phase]
        elif not started:
            hint = "按下開始，進入預備倒數"
        else:
            hint = "已暫停，按下繼續"

        badge = phase.upper() if running else "READY"

        button = (
            "暫停" if running
            else "繼續" if started
            else "開始運動"
        )

        duration = duration_of(phase)

        fraction = max(
            0,
            min(1, (duration - remaining) / duration)
        )

    el("phase-label").textContent = titles[phase]
    el("phase-label").style.color = color

    el("hint").textContent = hint
    el("status-pill").textContent = badge
    el("start-btn").textContent = button

    percent = fraction * 100

    el("progress-fill").style.width = f"{percent:.2f}%"
    el("progress-fill").style.backgroundColor = color

    el("ring").style.background = (
        f"conic-gradient({color} {percent:.2f}%, "
        f"#35455c 0%)"
    )

    for name in ("prep", "work", "rest", "round"):
        el(f"{name}-minus").disabled = running
        el(f"{name}-plus").disabled = running


# ===== 重設 =====
def reset_state():
    global round_no, phase, running, started
    global remaining, deadline, last_countdown

    window.speechSynthesis.cancel()

    round_no = 1
    phase = "prep"
    running = False
    started = False
    remaining = float(prep)
    deadline = None
    last_countdown = None

    render()


# ===== 切換階段 =====
def advance_phase():
    global round_no, phase, running, started
    global remaining, deadline, last_countdown

    if phase == "prep":
        phase = "work"
        length = work
        message = "Go!"

    elif phase == "work":
        if round_no >= rounds:
            phase = "done"
            running = False
            started = False
            remaining = 0
            deadline = None
            last_countdown = None

            speak("Workout complete!")
            return

        phase = "rest"
        length = rest
        message = "Rest!"

    elif phase == "rest":
        round_no += 1
        phase = "work"
        length = work
        message = "Go!"

    else:
        return

    remaining = float(length)

    # 延續時間軸，避免累積誤差
    deadline += length * 1000
    last_countdown = None

    speak(message)


# ===== 每個階段最後三秒倒數 =====
def announce_countdown():
    global last_countdown

    if phase not in ("prep", "work", "rest"):
        return

    secs = math.ceil(remaining)

    if secs in (3, 2, 1):
        if last_countdown != secs:
            last_countdown = secs

            messages = {
                3: "Three",
                2: "Two",
                1: "One"
            }

            speak(messages[secs])


# ===== 計時器 =====
def tick():
    global remaining

    if not running:
        return

    now = window.performance.now()

    while (
        running
        and deadline is not None
        and now >= deadline
    ):
        advance_phase()

    if running:
        remaining = max(
            0,
            (deadline - now) / 1000
        )

        announce_countdown()

    render()


# ===== 開始 / 暫停 / 繼續 =====
@when("click", "#start-btn")
def toggle(event):
    global phase, running, started
    global remaining, deadline, last_countdown
    global round_no

    if phase == "done":
        reset_state()

    if running:
        remaining = max(
            0,
            (deadline - window.performance.now()) / 1000
        )

        running = False
        deadline = None
        window.speechSynthesis.cancel()

    else:
        if not started:
            round_no = 1
            phase = "prep"
            remaining = float(prep)
            last_countdown = None

            speak("Get ready!")

        started = True
        running = True

        deadline = (
            window.performance.now() + remaining * 1000
        )

    render()


# ===== 重設按鈕 =====
@when("click", "#reset-btn")
def reset(event):
    reset_state()


# ===== 調整設定 =====
@when("click", ".stepper button")
def change(event):
    global prep, work, rest, rounds

    if running:
        return

    name = str(event.currentTarget.id)
    step = 1 if name.endswith("plus") else -1

    if name.startswith("prep"):
        prep = max(5, min(120, prep + step * 5))

    elif name.startswith("work"):
        work = max(5, min(3600, work + step * 5))

    elif name.startswith("rest"):
        rest = max(5, min(3600, rest + step * 5))

    elif name.startswith("round"):
        rounds = max(1, min(100, rounds + step))

    reset_state()


# ===== 初始化 =====
reset_state()

el("start-btn").disabled = False

tick_proxy = create_proxy(tick)
interval_id = window.setInterval(tick_proxy, 100)
