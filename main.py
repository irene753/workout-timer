"""FIT TIMER — PyScript timer with a preparation phase and spoken cues."""
import math
from pyscript import document, window, when
from pyscript.ffi import create_proxy

prep = 10
work = 40
rest = 20
rounds = 5
round_no = 1
phase = 'prep'  # prep, work, rest, done
running = False
remaining = float(prep)
deadline = None
last_countdown = None


def el(name):
    return document.getElementById(name)


def speak(message):
    """Uses browser speech synthesis; may be restricted in background on iOS."""
    synth = window.speechSynthesis
    if not synth:
        return
    synth.cancel()
    utterance = window.SpeechSynthesisUtterance.new(message)
    utterance.lang = 'zh-TW'
    utterance.rate = 1.0
    utterance.volume = 1.0
    synth.speak(utterance)


def duration_of(p):
    return {'prep': prep, 'work': work, 'rest': rest}.get(p, 1)


def render():
    secs = max(0, math.ceil(remaining))
    el('time-label').textContent = f'{secs // 60:02d}:{secs % 60:02d}'
    for item, value, suffix in [('prep', prep, '秒'), ('work', work, '秒'), ('rest', rest, '秒'), ('round', rounds, '組')]:
        el(f'{item}-value').textContent = f'{value} {suffix}'
    el('round-label').textContent = f'第 {round_no} / {rounds} 組'
    if phase == 'done':
        title, hint, badge, button, color = '運動完成 🎉', '做得很好！', 'DONE', '再做一次', '#2bd3b3'
        fraction = 1.0
    else:
        titles = {'prep': '預備時間', 'work': '運動時間', 'rest': '休息時間'}
        colors = {'prep': '#82b4ff', 'work': '#2bd3b3', 'rest': '#ffc06a'}
        title = titles[phase]
        color = colors[phase]
        hint = '準備好！' if running and phase == 'prep' else '持續加油！' if running and phase == 'work' else '恢復呼吸' if running and phase == 'rest' else '按下開始繼續'
        badge = phase.upper() if running else 'PAUSED'
        button = '暫停' if running else '開始 / 繼續'
        duration = duration_of(phase)
        fraction = max(0, min(1, (duration - remaining) / duration))
    el('phase-label').textContent = title
    el('phase-label').style.color = color
    el('hint').textContent = hint
    el('status-pill').textContent = badge
    el('start-btn').textContent = button
    el('progress-fill').style.width = f'{fraction * 100:.2f}%'
    el('progress-fill').style.backgroundColor = color
    el('ring').style.background = f'conic-gradient({color} {fraction * 100:.2f}%, #35455c 0%)'
    for name in ('prep', 'work', 'rest', 'round'):
        el(f'{name}-minus').disabled = running
        el(f'{name}-plus').disabled = running


def reset_state():
    global round_no, phase, running, remaining, deadline, last_countdown
    window.speechSynthesis.cancel()
    round_no, phase, running = 1, 'prep', False
    remaining, deadline, last_countdown = float(prep), None, None
    render()


def advance_phase():
    global round_no, phase, running, remaining, deadline, last_countdown
    if phase == 'prep':
        phase, length, phrase = 'work', work, '開始！'
    elif phase == 'work':
        if round_no >= rounds:
            phase, running, remaining, deadline = 'done', False, 0, None
            last_countdown = None
            speak('運動完成！')
            return
        phase, length, phrase = 'rest', rest, '休息！'
    else:
        round_no += 1
        phase, length, phrase = 'work', work, '開始！'
    remaining = float(length)
    deadline += length * 1000
    last_countdown = None
    speak(phrase)


def tick():
    global remaining, last_countdown
    if not running:
        return
    now = window.performance.now()
    while running and now >= deadline:
        advance_phase()
    if running:
        remaining = max(0, (deadline - now) / 1000)
        secs = math.ceil(remaining)
        # Only speak a countdown once per second, during preparation.
        if phase == 'prep' and secs in (3, 2, 1) and last_countdown != secs:
            last_countdown = secs
            speak({3: '三', 2: '二', 1: '一'}[secs])
    render()


@when('click', '#start-btn')
def toggle(event):
    global running, deadline, remaining
    if phase == 'done':
        reset_state()
    if running:
        remaining = max(0, (deadline - window.performance.now()) / 1000)
        running, deadline = False, None
        window.speechSynthesis.cancel()
    else:
        running = True
        deadline = window.performance.now() + remaining * 1000
        # The first utterance occurs inside the user click gesture.
        if phase == 'prep' and remaining == float(prep):
            speak('預備！')
    render()


@when('click', '#reset-btn')
def reset(event):
    reset_state()


@when('click', '.stepper button')
def change(event):
    global prep, work, rest, rounds
    if running:
        return
    name = str(event.currentTarget.id)
    step = 1 if name.endswith('plus') else -1
    if name.startswith('prep'):
        prep = max(5, min(120, prep + step * 5))
    elif name.startswith('work'):
        work = max(5, min(3600, work + step * 5))
    elif name.startswith('rest'):
        rest = max(5, min(3600, rest + step * 5))
    else:
        rounds = max(1, min(100, rounds + step))
    reset_state()


reset_state()
el('start-btn').disabled = False
tick_proxy = create_proxy(tick)
interval_id = window.setInterval(tick_proxy, 100)
