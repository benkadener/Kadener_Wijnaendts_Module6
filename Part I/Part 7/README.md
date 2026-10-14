# Part 7: Experimental Goldilocks Plots

This part provides the experimental results needed for A3 Question 2.

## Matched conditions

Use the same apparatus and settings for all six retained runs.

| Setting | Value |
|---|---:|
| Lower setpoint (°C) | 15 |
| Upper setpoint (°C) | 32.5 |
| PWM limit | 255 |
| Sample interval (s) | Approximately 0.12 |
| Anti-windup | Enabled |

Each run must include:

1. An upward step from the lower to the upper setpoint.
2. A downward step from the upper to the lower setpoint.
3. Enough time to settle, or a note that it did not settle.

Set PWM to zero before changing controller mode or resetting the integral. Press **Zero integral** before every PI run.

## Six required runs

For P runs, use $K_i=0$. For PI runs, select one $K_p$ and hold it fixed while changing only $K_i$.

| Run | Controller | $K_p$ (PWM/°C) | $K_i$ (PWM/(°C·s)) | Initial temperature (°C) | Data filename | Plot filename |
|---:|:---:|---:|---:|---:|---|---|
| 1 | P, low gain | 20 | 0 | 26.61 | `Low_kp_Heating.csv`, `Low_kp_Cooling.csv` | `01_p_low.png` |
| 2 | P, medium gain | 60 | 0 | 16.92 | `Medium_kp_Heating.csv`, `Medium_kp_Cooling.csv` | `02_p_medium.png` |
| 3 | P, high gain | 200 | 0 | 15.23 | `High_kp_Heating.csv`, `High_kp_Cooling.csv` | `03_p_high.png` |
| 4 | PI, low $K_i$ | 55 | 0.08 | 15.63 | `Low_ki_Heating.csv`, `Low_ki_Cooling.csv` | `04_pi_low.png` |
| 5 | PI, medium $K_i$ | 55 | 0.30 | 15.77 | `Medium_ki_Heating.csv`, `Medium_ki_Cooling.csv` | `05_pi_medium.png` |
| 6 | PI, high $K_i$ | 55 | 0.80 | 15.05 | `High_ki_Heating.csv`, `High_ki_Cooling.csv` | `06_pi_high.png` |

## Required plots

Make one clearly labeled plot for each run. Every plot must show:

- measured temperature and setpoint;
- applied signed PWM; and
- controller mode, $K_p$, and $K_i$.

## Step-response metrics

Calculate these metrics only for Run 3 (highest-gain P) and Run 6 (highest-gain PI), for both directions.

Use:

- **Rise time:** time from 10% to 90% of the final temperature change.
- **Settling time:** time after which the temperature remains within ±2% of the final temperature change.
- **Percent overshoot:** $100(T_{\mathrm{peak}}-T_{\mathrm{final}})/|T_{\mathrm{final}}-T_{\mathrm{initial}}|$ for an upward step, using the corresponding magnitude for a downward step.
- **Steady-state error:** $T_{\mathrm{set}}-T_{\mathrm{ss}}$.
- **Oscillation period:** time between successive peaks, when oscillation is present.

| Metric | High-P upward | High-P downward | High-PI upward | High-PI downward |
|---|---:|---:|---:|---:|
| Rise time (s) | 5.87 | 14.41 | 6.00 | 15.95 |
| Percent overshoot (%) | 12.91 | 1.54 | 6.31 | 0.22 |
| Settling time (s) | Did not settle | 25.87 | 29.34 | 49.63 |
| Steady-state error (°C) | 0.06 | -0.20 | 0.02 | approximately 0.00 |
| Oscillation period (s), if applicable | 6.63 | N/A | N/A | N/A |

The high-P upward response did not enter and remain inside the ±2% settling band because it sustained an oscillation. Its measured oscillation period was approximately $6.63\ \mathrm{s}$. The other three responses did not contain enough repeated peaks to assign an oscillation period reliably.

## Files to preserve

Save the CSV data and plot for every retained run. The saved data must include temperature, setpoint, applied signed PWM, $u_P$, $u_I$, and total requested command.

Generate all six plots and the high-gain metrics table from the saved CSV files with:

```bash
python3 "Part 7/analyze_goldilocks.py"
```

The results are saved in `Part 7/analysis_output/`.

Stop and set PWM to zero if the temperature moves in the wrong direction, the display freezes, saturation persists unexpectedly, or oscillations grow.
