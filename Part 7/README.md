# Part 7: PI Control and Experimental Goldilocks Plots

## Before applying power

- [ ] Show the instructor the calculations for $e$, $q$, $u_P$, $u_I$, requested $u$, and clamped applied $u$ in `python_GUI.py`.
- [ ] Confirm that conditional-integration anti-windup is enabled.
- [ ] Confirm that the Arduino temperature shutdown and PWM clamp still work.
- [ ] Set PWM to zero before changing controller mode or resetting the integral.

## Matched conditions

Use these same conditions for all six retained runs:

| Setting | Value |
|---|---:|
| Lower setpoint |  |
| Upper setpoint |  |
| PWM limit | 255 |
| Sample interval |  |
| Anti-windup | Enabled |

Each run must include both steps:

1. Begin settled at the lower setpoint.
2. Change to the upper setpoint and allow it to settle.
3. Change back to the lower setpoint and allow it to settle.

## Six retained runs

For P runs, use $K_i=0$. For PI runs, hold one $K_p$ fixed and change only $K_i$. Press **Zero integral** before every PI run.

| Run | Controller | $K_p$ (PWM/°C) | $K_i$ (PWM/(°C·s)) | Purpose | Initial temperature (°C) | Data filename | Plot filename |
|---:|:---:|---:|---:|---|---:|---|---|
| 1 | P | 2 | 0 | Low gain: slow response or large droop |  |  |  |
| 2 | P | 10 | 0 | Intermediate gain: best P compromise |  |  |  |
| 3 | P | 60 | 0 | High gain: overshoot or ringing |  |  |  |
| 4 | PI |  |  | Low $K_i$: slow integral correction |  |  |  |
| 5 | PI | Same as Run 4 |  | Intermediate $K_i$: best PI compromise |  |  |  |
| 6 | PI | Same as Run 4 |  | High $K_i$: excess overshoot, ringing, or saturation |  |  |  |

## Required observations

| Check | Result |
|---|---|
| Does $u_I$ grow while persistent error remains? |  |
| Is PI steady-state error smaller than P-only error? |  |
| Which P run gives the best compromise? |  |
| Which PI run gives the best compromise? |  |

Save temperature, setpoint, error, $u_P$, $u_I$, requested signed PWM, and applied signed PWM for every retained run.

Stop control and set PWM to zero if the temperature moves in the wrong direction, the display freezes, saturation persists unexpectedly, or oscillations grow.
