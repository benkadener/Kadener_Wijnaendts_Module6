| Change | Damping ratio $\zeta$ | What happens |
|---|---|---|
| Increase $K_i$: 0.10 → 0.60 → 1.00, with $K_p=18$ | 2.419 → 0.987 → 0.765 | More overshoot and ringing. |
| Increase $K_p$: 18 → 36, with $K_i=0.60$ | 0.987 → 1.869 | More damping; no ringing in the saved late-time view. |
| Double $C$: 130 → 260 J/K; keep other settings fixed | 0.996 → 0.704 | Slower response and more overshoot. |

| Two-lump PI: $K_p=18$, $G=2$ W/K, $K_{i,\mathrm{crit}}\approx2.34$ PWM/(°C·s) | $\rho_I=K_i/K_{i,\mathrm{crit}}$ | What happens |
|---|---|---|
| $K_i=0.26$ | 0.111 | Small overshoot; oscillations decay quickly. |
| $K_i=1.00$ | 0.427 | Larger overshoot; oscillations decay. |
| $K_i=2.10$ | 0.897 | Large oscillations; weak decay in the displayed interval. |
| $K_i=2.50$ | 1.068 | Oscillations slowly grow; unstable. |
