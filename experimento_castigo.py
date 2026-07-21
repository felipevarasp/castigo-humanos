#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Control por valor del castigo instrumental en humanos
(análogo humano de Varas, Dickinson & Perez, 2026, "Value control of punishment")

PREGUNTA
--------
¿La conducta instrumental suprimida por castigo está guiada por el VALOR ACTUAL
del estímulo aversivo? Se manipula el valor del castigador (sonido aversivo) por
CONTRACONDICIONAMIENTO (sonido → puntos) o HABITUACIÓN (presentaciones repetidas
del sonido) y se evalúa en una prueba en EXTINCIÓN (sin el estímulo revalorizado).

FASES
-----
  1. Entrenamiento    — 1 sesión × 6 bloques × 2 min (q y p → fichas, RI-15 s)
  2. Castigo          — 2 sesiones × 3 bloques × 2 min (una tecla castigada con
                        sonido en RF individualizado: ~10 sonidos/bloque a tasa basal)
  3. Revalorización   — 20 eventos (según grupo):
                          · Contracondicionamiento: sonido → puntos
                          · Habituación: sonido solo, repetido
  4. Prueba extinción — 1 bloque × 2 min (fichas siguen; SIN sonido)
  5. Prueba reforzada — 1 bloque × 2 min (vuelve el sonido, mismas contingencias)
  6. Cierre

CONTRABALANCEO (según ID)
-------------------------
  grupo        = 'contracond'  si pid par   else 'habituacion'
  tecla_castigo= 'q'           si (pid//2) par else 'p'
  (cruza grupo × tecla castigada con pid % 4)

PROGRAMAS
---------
  Fichas: RI-15 s independiente por tecla (intervalo ~ Exp(15)); changeover
          (la 1.ª respuesta tras cambiar de tecla no obtiene ficha).
  Sonido: RF individualizado = round(respuestas_tecla_castigo_ultimo_bloque / 10),
          superpuesto (cuenta todas las respuestas de la tecla castigada).

DATOS: CSV en ./data/castigo_sub_{id}_{timestamp}.csv
"""
import os
import csv
import random
from datetime import datetime

import numpy as np

# ── Preferencias de audio ANTES de importar sound ─────────────
from psychopy import prefs
prefs.hardware['audioLib'] = ['ptb', 'sounddevice', 'pyo', 'pygame']

from psychopy import visual, core, event, gui, sound

# ═══════════════════════════════════════════════════════════════
#  PARÁMETROS
# ═══════════════════════════════════════════════════════════════
TRAIN_DURATION   = 120   # s por bloque de entrenamiento
PUNISH_DURATION  = 120   # s por bloque de castigo
TEST_DURATION    = 120   # s por bloque de prueba (extinción / reforzada)

N_TRAIN_SESSIONS        = 1  # sesiones de entrenamiento
N_TRAIN_BLOCKS_SESSION  = 6  # bloques por sesión de entrenamiento
N_PUNISH_SESSIONS       = 2  # sesiones de castigo
N_PUNISH_BLOCKS_SESSION = 3  # bloques por sesión de castigo
N_TEST_BLOCKS          = 1   # bloques por prueba (extinción y reforzada)

RI_T             = 15.0  # media del intervalo RI de fichas (s)
TARGET_SOUNDS    = 10    # sonidos objetivo por bloque de castigo (a tasa basal)
N_REVAL_EVENTS   = 20    # eventos de revalorización por grupo

COIN_FLASH_S     = 0.5   # duración del flash de ficha (s)
POINTS_FLASH_S   = 0.9   # duración del "+puntos" en contracondicionamiento (s)
COIN_RADIUS      = 0.055 # radio de ficha (unidades de altura)

POINTS_PER_TOKEN = 10    # puntos por ficha recolectada
POINTS_PER_REVAL = 50    # puntos por evento de contracondicionamiento

REVAL_ISI_MIN    = 2.0   # ITI mínimo entre eventos de revalorización (s)
REVAL_ISI_MAX    = 4.0   # ITI máximo (s)
SOUND_DUR_GUESS  = 0.6   # espera aprox. tras disparar el sonido (s)

# ── Colores PsychoPy (escala −1 a 1) ──────────────────────────
C_BG    = ( 0.30,  0.30,  0.30)
C_WHITE = ( 1.00,  1.00,  1.00)
C_BLACK = (-1.00, -1.00, -1.00)
C_LGRAY = ( 0.75,  0.75,  0.75)
C_DGRAY = ( 0.10,  0.10,  0.10)
C_GREEN = (-0.60,  0.85, -0.60)

COIN_RGB = {
    'blue' : (-0.60, -0.60,  1.00),
    'red'  : ( 1.00, -0.60, -0.60),
    'gold' : ( 1.00,  0.80, -0.30),
}

# ── Posiciones de teclas (unidades de altura) ──────────────────
KEY_POS = {
    'q': (-0.42, 0.0),
    'p': ( 0.42, 0.0),
}
KEY_BOX = 0.10   # lado del cuadrado indicador de tecla

# Color de ficha asociado a cada tecla (fijo)
KEY_TOKEN = {'q': 'blue', 'p': 'red'}

# ═══════════════════════════════════════════════════════════════
#  DIÁLOGO DE PARTICIPANTE
# ═══════════════════════════════════════════════════════════════
dlg = gui.Dlg(title='Experimento de Aprendizaje (Castigo)')
dlg.addField('ID Participante:')
dlg.show()
if not dlg.OK:
    core.quit()
PARTICIPANT_ID = str(dlg.data[0]).strip()
try:
    _pid = int(PARTICIPANT_ID)
except ValueError:
    _pid = abs(hash(PARTICIPANT_ID)) % 1000

# ═══════════════════════════════════════════════════════════════
#  CONTRABALANCEO
# ═══════════════════════════════════════════════════════════════
GROUP        = 'contracond' if _pid % 2 == 0 else 'habituacion'
PUNISHED_KEY = 'q' if (_pid // 2) % 2 == 0 else 'p'
CONTROL_KEY  = 'p' if PUNISHED_KEY == 'q' else 'q'
ACTIVE_KEYS  = ['q', 'p']

# ═══════════════════════════════════════════════════════════════
#  SONIDO AVERSIVO
# ═══════════════════════════════════════════════════════════════
_HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
SOUND_PATH = os.path.join(_HERE, 'loud_bang.wav')
try:
    AVERSIVE = sound.Sound(SOUND_PATH)
    _SOUND_OK = True
except Exception as _e:
    print('ADVERTENCIA: no se pudo cargar el sonido (%s): %s' % (SOUND_PATH, _e))
    AVERSIVE = None
    _SOUND_OK = False


def play_aversive():
    """Reproduce el sonido aversivo desde el inicio."""
    if AVERSIVE is not None:
        try:
            AVERSIVE.stop()
        except Exception:
            pass
        AVERSIVE.play()

# ═══════════════════════════════════════════════════════════════
#  ARCHIVO DE DATOS
# ═══════════════════════════════════════════════════════════════
os.makedirs('data', exist_ok=True)
_ts       = datetime.now().strftime('%Y%m%d_%H%M%S')
DATA_PATH = os.path.join('data', f'castigo_sub_{PARTICIPANT_ID}_{_ts}.csv')
_df = open(DATA_PATH, 'w', newline='', encoding='utf-8')
_dw = csv.writer(_df)
_dw.writerow([
    'participant', 'group', 'punished_key', 'control_key', 'fr',
    'phase', 'session', 'block', 't_block', 't_global',
    'event', 'key', 'token_color', 'token_earned', 'sound_played', 'points',
    'rss', 'last_key',
    'resp_q', 'resp_p', 'tokens_block', 'sounds_block',
])

_GCK  = core.Clock()          # reloj global
STATE = {'points': 0, 'fr': 0}  # estado persistente entre fases


def _log(phase, session, block, t_blk, evtype,
         key='', color='', token_earned=False, sound_played=False,
         rss='', last_key='',
         resp_q='', resp_p='', tokens_block='', sounds_block=''):
    _dw.writerow([
        PARTICIPANT_ID, GROUP, PUNISHED_KEY, CONTROL_KEY, STATE['fr'],
        phase, session, block, round(t_blk, 4), round(_GCK.getTime(), 4),
        evtype, key, color, int(bool(token_earned)), int(bool(sound_played)),
        STATE['points'], rss, last_key,
        resp_q, resp_p, tokens_block, sounds_block,
    ])
    _df.flush()

# ═══════════════════════════════════════════════════════════════
#  VENTANA Y ESTÍMULOS
# ═══════════════════════════════════════════════════════════════
win = visual.Window(
    fullscr=True, color=C_BG, units='height',
    allowGUI=False, monitor='testMonitor'
)
win.mouseVisible = False

_krects = {k: visual.Rect(win, KEY_BOX, KEY_BOX, pos=p,
                          fillColor=C_LGRAY, lineColor=C_DGRAY)
           for k, p in KEY_POS.items()}
_klabs  = {k: visual.TextStim(win, k.upper(), pos=p,
                              color=C_BLACK, height=0.050, bold=True)
           for k, p in KEY_POS.items()}

# Ficha (se recolorea según resultado)
_coin = visual.Circle(win, radius=COIN_RADIUS, pos=(0, 0),
                      fillColor=COIN_RGB['blue'], lineColor=None)

# HUD (temporizador + puntos)
_hud_t = visual.TextStim(win, '', pos=(0,  0.44), color=C_LGRAY, height=0.030)
_hud_s = visual.TextStim(win, '', pos=(0, -0.44), color=C_LGRAY, height=0.032)

# Texto de mensaje genérico
_msg = visual.TextStim(win, '', pos=(0, 0), color=C_WHITE,
                       height=0.045, wrapWidth=1.50, alignText='center')

# Fijación central (revalorización)
_fix = visual.TextStim(win, '+', pos=(0, 0), color=C_LGRAY, height=0.08)

# "+puntos" para contracondicionamiento
_plus = visual.TextStim(win, '', pos=(0, 0), color=C_GREEN, height=0.10, bold=True)

# ═══════════════════════════════════════════════════════════════
#  UTILIDADES
# ═══════════════════════════════════════════════════════════════
def _quit(pressed):
    if 'escape' in pressed:
        try:
            _df.close()
        except Exception:
            pass
        win.close()
        core.quit()


def show_msg(text, key='space'):
    """Pantalla de mensaje; espera barra espaciadora."""
    _msg.text = text
    event.clearEvents()
    while True:
        _msg.draw()
        win.flip()
        pressed = event.getKeys([key, 'escape'])
        _quit(pressed)
        if key in pressed:
            break


def _draw_keys():
    for k in ACTIVE_KEYS:
        _krects[k].draw()
        _klabs[k].draw()


def _next_iti():
    """Intervalo inter-ficha aleatorio ~ Exp(RI_T)."""
    return np.random.exponential(RI_T)

# ═══════════════════════════════════════════════════════════════
#  BLOQUE OPERANTE (núcleo)
# ═══════════════════════════════════════════════════════════════
def run_operant_block(phase, session, block_num, duration,
                      deliver_sound=False, show_points=True):
    """
    Ejecuta un bloque operante con q y p activas.

    Fichas: RI-15 s independiente por tecla + changeover.
    Sonido: si deliver_sound, cada FR (STATE['fr']) respuestas en PUNISHED_KEY
            dispara el sonido aversivo (programa superpuesto).

    Retorna dict con conteos de respuestas, fichas y sonidos.
    """
    fr = STATE['fr']

    # Programas RI de fichas
    t_remaining = {k: _next_iti() for k in ACTIVE_KEYS}
    avail       = {k: False for k in ACTIVE_KEYS}

    # Changeover
    last_key = None
    rss      = 0

    # Contadores
    resp   = {k: 0 for k in ACTIVE_KEYS}
    tokens = {k: 0 for k in ACTIVE_KEYS}
    punish_counter = 0
    n_sounds = 0

    # Flash de ficha
    flash_on  = False
    flash_col = ''
    t_onset   = 0.0

    blk_clk = core.Clock()
    prev_t  = 0.0
    event.clearEvents()

    while True:
        t  = blk_clk.getTime()
        dt = t - prev_t
        prev_t = t
        if t >= duration:
            break

        # Actualizar relojes RI
        for k in ACTIVE_KEYS:
            if not avail[k]:
                t_remaining[k] -= dt
                if t_remaining[k] <= 0:
                    avail[k] = True

        # Timeout del flash de ficha
        if flash_on and (t - t_onset) >= COIN_FLASH_S:
            flash_on = False

        # Dibujar
        _draw_keys()
        if flash_on:
            _coin.fillColor = COIN_RGB[flash_col]
            _coin.draw()
        remaining   = max(0, duration - t)
        _hud_t.text = f'{int(remaining // 60):02d}:{int(remaining % 60):02d}'
        _hud_t.draw()
        if show_points:
            _hud_s.text = f'Puntos: {STATE["points"]}'
            _hud_s.draw()
        win.flip()

        # Capturar teclas
        pressed = event.getKeys(keyList=ACTIVE_KEYS + ['escape'])
        _quit(pressed)
        for k in pressed:
            if k not in ACTIVE_KEYS:
                continue
            resp[k] += 1

            # ── Changeover para fichas ──────────────────────
            if last_key is None:
                rss      = 1
                can_earn = True
            elif k == last_key:
                rss     += 1
                can_earn = True
            else:
                rss      = 1
                can_earn = False
            last_key = k

            token_earned = False
            color        = ''
            if can_earn and avail[k]:
                token_earned   = True
                color          = KEY_TOKEN[k]
                avail[k]       = False
                t_remaining[k] = _next_iti()
                tokens[k]     += 1
                STATE['points'] += POINTS_PER_TOKEN
                flash_on  = True
                flash_col = color
                t_onset   = t

            # ── Castigo (RF superpuesto en la tecla castigada) ──
            sound_played = False
            if deliver_sound and k == PUNISHED_KEY and fr > 0:
                punish_counter += 1
                if punish_counter >= fr:
                    punish_counter = 0
                    play_aversive()
                    sound_played = True
                    n_sounds    += 1

            _log(phase, session, block_num, t,
                 'response', key=k, color=color,
                 token_earned=token_earned, sound_played=sound_played,
                 rss=rss, last_key=last_key)

    # Resumen del bloque
    _log(phase, session, block_num, duration, 'block_end',
         resp_q=resp['q'], resp_p=resp['p'],
         tokens_block=tokens['q'] + tokens['p'], sounds_block=n_sounds)

    return {'resp': resp, 'tokens': tokens, 'sounds': n_sounds}

# ═══════════════════════════════════════════════════════════════
#  REVALORIZACIÓN
# ═══════════════════════════════════════════════════════════════
def run_counterconditioning():
    """Contracondicionamiento: sonido → puntos (N_REVAL_EVENTS pares)."""
    for i in range(N_REVAL_EVENTS):
        # ISI con fijación
        iti = random.uniform(REVAL_ISI_MIN, REVAL_ISI_MAX)
        _iti_clk = core.Clock()
        while _iti_clk.getTime() < iti:
            _fix.draw()
            win.flip()
            _quit(event.getKeys(['escape']))

        # Sonido
        play_aversive()
        _log('reval_cc', i + 1, 0, _GCK.getTime(), 'reval_sound',
             sound_played=True)
        _s_clk = core.Clock()
        while _s_clk.getTime() < SOUND_DUR_GUESS:
            _fix.draw()
            win.flip()
            _quit(event.getKeys(['escape']))

        # Puntos (consecuencia apetitiva)
        STATE['points'] += POINTS_PER_REVAL
        _plus.text = f'+{POINTS_PER_REVAL}'
        _log('reval_cc', i + 1, 0, _GCK.getTime(), 'reval_points')
        _p_clk = core.Clock()
        while _p_clk.getTime() < POINTS_FLASH_S:
            _coin.fillColor = COIN_RGB['gold']
            _coin.draw()
            _plus.draw()
            win.flip()
            _quit(event.getKeys(['escape']))


def run_habituation():
    """Habituación: presentaciones repetidas del sonido (N_REVAL_EVENTS)."""
    for i in range(N_REVAL_EVENTS):
        iti = random.uniform(REVAL_ISI_MIN, REVAL_ISI_MAX)
        _iti_clk = core.Clock()
        while _iti_clk.getTime() < iti:
            _fix.draw()
            win.flip()
            _quit(event.getKeys(['escape']))

        play_aversive()
        _log('reval_hab', i + 1, 0, _GCK.getTime(), 'reval_sound',
             sound_played=True)
        _s_clk = core.Clock()
        while _s_clk.getTime() < SOUND_DUR_GUESS:
            _fix.draw()
            win.flip()
            _quit(event.getKeys(['escape']))

# ═══════════════════════════════════════════════════════════════
#  FLUJO PRINCIPAL
# ═══════════════════════════════════════════════════════════════
# ── Bienvenida ────────────────────────────────────────────────
show_msg(
    'Bienvenido/a al experimento.\n\n'
    'Tu objetivo es ganar la mayor cantidad de PUNTOS posible\n'
    'presionando las teclas del teclado.\n\n'
    'Cada tecla que uses puede entregarte fichas que valen puntos.\n\n'
    'Presiona espacio para continuar.'
)
show_msg(
    'Las teclas disponibles son:\n\n'
    '        Q  (izquierda)                 P  (derecha)\n\n'
    'Puedes presionarlas cuando quieras y en el orden que quieras.\n'
    'No siempre entregan una ficha: a veces hay que insistir.\n\n'
    'Al cambiar de una tecla a la otra, la PRIMERA presión en la\n'
    'nueva tecla no entrega ficha; debes presionarla al menos dos veces.\n\n'
    'Presiona espacio para comenzar.'
)

# ── FASE 1 · ENTRENAMIENTO ───────────────────────────────────
show_msg('FASE 1: ENTRENAMIENTO\n\nPresiona espacio para comenzar.')
for s in range(1, N_TRAIN_SESSIONS + 1):
    if s > 1:
        show_msg(
            f'Fin de la sesión {s - 1} de entrenamiento.\n\n'
            'Puedes tomar un breve descanso.\n\n'
            'Presiona espacio para continuar con la siguiente sesión.'
        )
    for b in range(1, N_TRAIN_BLOCKS_SESSION + 1):
        show_msg(
            f'Sesión {s} · Bloque {b} de {N_TRAIN_BLOCKS_SESSION}\n\n'
            'Presiona espacio para comenzar.'
        )
        last_train = run_operant_block('training', s, b, TRAIN_DURATION,
                                       deliver_sound=False)

# ── Calcular RF individualizado para el castigo ───────────────
_base_resp = last_train['resp'][PUNISHED_KEY]
STATE['fr'] = max(1, int(round(_base_resp / float(TARGET_SOUNDS))))
_log('fr_calc', 0, 0, _GCK.getTime(), 'fr_set',
     key=PUNISHED_KEY, resp_q=last_train['resp']['q'],
     resp_p=last_train['resp']['p'])

# ── FASE 2 · CASTIGO ─────────────────────────────────────────
show_msg(
    'FASE 2\n\n'
    'La tarea continúa igual: sigue ganando puntos con las teclas.\n\n'
    'A veces podrás escuchar un SONIDO FUERTE mientras respondes.\n\n'
    'Presiona espacio para comenzar.'
)
for s in range(1, N_PUNISH_SESSIONS + 1):
    if s > 1:
        show_msg(
            f'Fin de la sesión {s - 1} de esta fase.\n\n'
            'Puedes tomar un breve descanso.\n\n'
            'Presiona espacio para continuar con la siguiente sesión.'
        )
    for b in range(1, N_PUNISH_BLOCKS_SESSION + 1):
        show_msg(
            f'Sesión {s} · Bloque {b} de {N_PUNISH_BLOCKS_SESSION}\n\n'
            'Presiona espacio para comenzar.'
        )
        run_operant_block('punishment', s, b, PUNISH_DURATION, deliver_sound=True)

# ── FASE 3 · REVALORIZACIÓN ──────────────────────────────────
if GROUP == 'contracond':
    show_msg(
        'FASE 3\n\n'
        'En esta parte no usarás las teclas.\n'
        'Solo observa la pantalla y escucha con atención.\n\n'
        'Presiona espacio para comenzar.'
    )
    run_counterconditioning()
else:
    show_msg(
        'FASE 3\n\n'
        'En esta parte no usarás las teclas.\n'
        'Solo observa la pantalla y escucha con atención.\n\n'
        'Presiona espacio para comenzar.'
    )
    run_habituation()

# ── FASE 4 · PRUEBA EN EXTINCIÓN (sin sonido) ────────────────
show_msg(
    'FASE 4\n\n'
    'Vuelve la tarea de las teclas. Sigue ganando puntos como antes.\n\n'
    'Presiona espacio para comenzar.'
)
for b in range(1, N_TEST_BLOCKS + 1):
    run_operant_block('extinction_test', 1, b, TEST_DURATION,
                      deliver_sound=False)

# ── FASE 5 · PRUEBA REFORZADA (vuelve el sonido) ─────────────
show_msg(
    'FASE 5\n\n'
    'La tarea continúa. Sigue ganando puntos con las teclas.\n\n'
    'Presiona espacio para comenzar.'
)
for b in range(1, N_TEST_BLOCKS + 1):
    run_operant_block('reinforced_test', 1, b, TEST_DURATION,
                      deliver_sound=True)

# ── Cierre ────────────────────────────────────────────────────
show_msg(
    '¡Experimento finalizado!\n\n'
    f'Puntos totales: {STATE["points"]}\n\n'
    'Muchas gracias por tu participación.\n\n'
    'Presiona espacio para cerrar.'
)
_df.close()
win.close()
core.quit()
