# Control por valor del castigo instrumental en humanos

Análogo humano del estudio en ratas de **Varas, Dickinson & Perez (2026)**, *"Value control of punishment"* (*Psychonomic Bulletin & Review*), adaptando el paradigma libre-operante humano de **Perez et al. (2026)** (*BMC Psychology*).

## Pregunta de investigación

¿La conducta instrumental suprimida por castigo está guiada por el **valor actual** del estímulo aversivo? Se entrena una respuesta, se la castiga, se **revalúa** el castigador sin la respuesta presente, y se evalúa la respuesta en **extinción** (sin el estímulo revaluado). Si la supresión depende del valor del castigador, cambiar ese valor debería modificar la respuesta suprimida aun en su ausencia —lo que indicaría un control dirigido a metas, no un hábito insensible al valor.

La revalorización del castigador se manipula entre grupos:

- **Contracondicionamiento:** el sonido aversivo se asocia con una consecuencia apetitiva (ganancia directa de puntos).
- **Habituación:** el sonido aversivo se presenta repetidamente, solo.

## Archivos

| Archivo | Descripción |
|---|---|
| `experimento_castigo.py` | Experimento completo (sesión ≈ 35 min). |
| `experimento_castigo_DEMO.py` | Versión demo abreviada (≈ 4–5 min) que recorre todas las fases con bloques cortos. **No usar para recolectar datos.** |
| `loud_bang.wav` | Estímulo aversivo (sonido). Debe estar en la misma carpeta que el script. |
| `README.md` | Este archivo. |
| `LICENSE` | Licencia MIT (código). |
| `.gitignore` | Excluye datos de participantes y PDFs del repositorio. |

## Cómo ejecutarlo

1. Instalar **PsychoPy** (recomendado el *standalone* de [psychopy.org](https://www.psychopy.org), que incluye Python y las dependencias `numpy`, `sound`, etc.).
2. Mantener el script en la **misma carpeta** que `loud_bang.wav`.
3. Abrir el `.py` en PsychoPy Coder y presionar **Ejecutar** (▶), o desde terminal: `python experimento_castigo_DEMO.py`.
4. Ingresar un **ID de participante** en el diálogo inicial.
5. Avanzar con la **barra espaciadora**; salir en cualquier momento con **Esc**.

> **Para la demo:** el grupo depende de la paridad del ID. Usa un **ID par** para ver *contracondicionamiento* y uno **impar** para ver *habituación*. Conviene probar el volumen antes: el sonido debe ser claramente aversivo pero no molesto en exceso.

## Diseño

Dos teclas activas, **Q** y **P**, cada una asociada a una ficha de un color (azul/rojo) que otorga puntos. Una de las dos teclas será la castigada; la otra funciona como control dentro del mismo participante.

**Contrabalanceo (según el ID):** con `pid % 4` se cruzan grupo × tecla castigada, de modo que Q y P se castigan por igual entre participantes y ambos grupos quedan equilibrados.

| pid % 4 | Grupo | Tecla castigada |
|:---:|---|:---:|
| 0 | Contracondicionamiento | Q |
| 1 | Habituación | Q |
| 2 | Contracondicionamiento | P |
| 3 | Habituación | P |

### Fases (versión completa)

| # | Fase | Estructura | Qué ocurre |
|:---:|---|---|---|
| 1 | Entrenamiento | 1 sesión × 6 bloques × 2 min | Q y P entregan fichas en **RI-15 s** independiente por tecla, con *changeover*. |
| 2 | Castigo | 2 sesiones × 3 bloques × 2 min | Se mantienen las fichas; la **tecla castigada** produce además el **sonido** en un programa de razón fija individualizado. |
| 3 | Revalorización | 20 eventos | **Contracond.:** sonido → puntos. **Habituación:** sonido solo, repetido. (Sin teclas.) |
| 4 | Prueba en extinción | 1 bloque × 2 min | Se responde con fichas, pero **sin sonido**. Medida crítica. |
| 5 | Prueba reforzada | 1 bloque × 2 min | Vuelve el sonido con las mismas contingencias del castigo. |

En la **demo** todo se conserva pero reducido: entrenamiento 1×2, castigo 1×2, revalorización 4 eventos, pruebas 1 bloque, bloques de 25 s.

### Programas de refuerzo

- **Fichas (RI-15 s):** cada tecla tiene un reloj independiente; el intervalo entre fichas disponibles se muestrea de una exponencial de media 15 s. El *changeover* impide que la primera respuesta tras cambiar de tecla obtenga ficha (evita alternancia mecánica).
- **Sonido (RF individualizado):** al terminar el entrenamiento se calcula `RF = round(respuestas en la tecla castigada en el último bloque / 10)`, de modo que, a la tasa basal, el participante recibiría **~10 sonidos por bloque** de castigo. El programa es superpuesto: cuenta todas las respuestas de la tecla castigada.

## Datos de salida

Se guarda un CSV en `./data/` (prefijo `DEMO_` en la versión demo). Cada respuesta, ficha y sonido se registra fila a fila, más un resumen por bloque (`block_end`). Columnas clave: `group`, `punished_key`, `control_key`, `fr`, `phase`, `session`, `block`, `event`, `key`, `token_earned`, `sound_played`, `points`, y conteos por bloque (`resp_q`, `resp_p`, `tokens_block`, `sounds_block`).

**Contraste principal:** tasa de respuesta en la **tecla castigada vs. control** durante la **prueba en extinción**, comparada entre grupos. La predicción de un control por valor es que el contracondicionamiento recupere la respuesta castigada (reduce la supresión), mientras que la habituación la mantenga suprimida.

## Notas

- El backend de audio preferido es `ptb` (mayor precisión temporal); si falla, PsychoPy usa alternativas automáticamente.
- Todas las duraciones y números de bloque están como constantes al inicio del script, fáciles de ajustar.
- La contingencia del castigo **no** se revela en las instrucciones (se aprende durante la tarea).

## Referencias

- Varas, F. I., Dickinson, A., & Perez, O. D. (2026). Value control of punishment. *Psychonomic Bulletin & Review*, 33:194. https://doi.org/10.3758/s13423-026-02965-w
- Perez, O. D., Oh, S., Dickinson, A., Arenas, J., & Merlo, E. (2026). Human goal-directed behavior is resistant to interventions on the action-outcome contingency. *BMC Psychology*, 14:444. https://doi.org/10.1186/s40359-026-04115-2

---

*Contacto: Felipe Varas — felipe.varas@ug.uchile.cl*
