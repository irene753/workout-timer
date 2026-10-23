import math
from pyscript import document, window, when
from pyscript.ffi import create_proxy

prep, work, rest, rounds = 10, 40, 20, 5
round_no = 1
phase = 'prep'
running = False
started = False
remaining = float(prep)
deadline = None
last_countdown = None
current_utterance = None


def el(key):
    return document.getElementById(key)


def speak(message):
    global current_utterance
    synth = window.speechSynthesis
    synth.cancel()
    utterance = window.SpeechSynthesisUtterance.new(message)
    utterance.lang = 'en-US'
    utterance.rate = 1.1
    utterance.pitch = 1.0
    utterance.volume = 1.0
    voices = synth.getVoices()
    for voice in voices:
        if str(voice.lang).lower() == 'en-us':
            utterance.voice = voice
            break
    else:
        for voice in voices:
            if str(voice.lang).lower().startswith('en'):
                utterance.voice = voice
                break
    current_utterance = utterance
    synth.speak(utterance)


def duration_of(current):
    return {'prep': prep, 'work': work, 'rest': rest}.get(current, 1)


def render():
    seconds = max(0, math.ceil(remaining))
    el('time-label').textContent = f'{seconds // 60:02d}:{seconds % 60:02d}'
    for name, value, unit in (
        ('prep', prep, '秒'), ('work', work, '秒'),
        ('rest', rest, '秒'), ('round', rounds, '組')
    ):
        el(f'{name}-value').textContent = f'{value} {unit}'
    el('round-label').textContent = f'第 {round_no} / {rounds} 組'
    titles = {'prep': '預備時間', 'work': '運動時間',
              'rest': '休息時間', 'done': '運動完成 🎉'}
    colors = {'prep': '#82b4ff', 'work': '#008f7a',
              'rest': '#ffc06a', 'done': '#2bd3b3'}
    color = colors[phase]
    document.body.classList.toggle('work-mode', phase == 'work')

    if phase == 'done':
        hint, badge, button, fraction = '做得很好！', 'DONE', '再做一次', 1.0
    else:
        hints = {'prep': '準備開始運動！', 'work': '持續加油！',
                 'rest': '休息一下，準備下一組！'}
        hint = hints[phase] if running else ('已暫停，按下繼續' if started else '按下開始，進入預備倒數')
        badge = phase.upper() if running else 'READY'
        button = '暫停' if running else ('繼續' if started else '開始運動')
        fraction = max(0, min(1, (duration_of(phase) - remaining) / duration_of(phase)))

    el('phase-label').textContent = titles[phase]
    el('phase-label').style.color = color
    el('hint').textContent = hint
    el('status-pill').textContent = badge
    el('start-btn').textContent = button
    percent = fraction * 100
    el('progress-fill').style.width = f'{percent:.2f}%'
    el('progress-fill').style.backgroundColor = color
    el('ring').style.background = f'conic-gradient({color} {percent:.2f}%, #35455c 0%)'
    for name in ('prep', 'work', 'rest', 'round'):
        el(f'{name}-minus').disabled = running
        el(f'{name}-plus').disabled = running


def reset_state():
    global round_no, phase, running, started, remaining, deadline, last_countdown
    window.speechSynthesis.cancel()
    window.setTimerRunning(False)
    round_no, phase, running, started = 1, 'prep', False, False
    remaining, deadline, last_countdown = float(prep), None, None
    render()


def advance_phase():
    global round_no, phase, running, started, remaining, deadline, last_countdown
    if phase == 'prep':
        phase, length, message = 'work', work, 'Go!'
    elif phase == 'work':
        if round_no >= rounds:
            phase, running, started = 'done', False, False
            remaining, deadline, last_countdown = 0, None, None
            window.setTimerRunning(False)
            speak('Workout complete!')
            return
        phase, length, message = 'rest', rest, 'Rest!'
    elif phase == 'rest':
        round_no += 1
        phase, length, message = 'work', work, 'Go!'
    else:
        return
    remaining = float(length)
    deadline += length * 1000
    last_countdown = None
    speak(message)


def announce_countdown():
    global last_countdown
    secs = math.ceil(remaining)
    if phase in ('prep', 'work', 'rest') and secs in (3, 2, 1):
        if last_countdown != secs:
            last_countdown = secs
            speak({3: 'Three', 2: 'Two', 1: 'One'}[secs])


def tick():
    global remaining
    if not running:
        return
    now = window.performance.now()
    while running and deadline is not None and now >= deadline:
        advance_phase()
    if running:
        remaining = max(0, (deadline - now) / 1000)
        announce_countdown()
    render()


@when('click', '#start-btn')
def toggle(event):
    global phase, running, started, remaining, deadline, last_countdown, round_no
    if phase == 'done':
        reset_state()
    if running:
        remaining = max(0, (deadline - window.performance.now()) / 1000)
        running, deadline = False, None
        window.speechSynthesis.cancel()
        window.setTimerRunning(False)
    else:
        if not started:
            round_no, phase = 1, 'prep'
            remaining, last_countdown = float(prep), None
            speak('Get ready!')
        started, running = True, True
        deadline = window.performance.now() + remaining * 1000
        # 在使用者點擊事件觸發的流程中請求螢幕常亮
        window.setTimerRunning(True)
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
    elif name.startswith('round'):
        rounds = max(1, min(100, rounds + step))
    reset_state()


reset_state()
el('start-btn').disabled = False
tick_proxy = create_proxy(tick)
interval_id = window.setInterval(tick_proxy, 100)
