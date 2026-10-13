# Part 4: Simulation Results

## 1. Guided open-loop runs

Select `one_lump`, `measured`, and `open_loop`. Use:

$$
T_{\mathrm{amb}}=22^\circ\mathrm C,\quad
\chi_h=0.46\ ^\circ\mathrm C/\mathrm{PWM},\quad
\chi_c=0.23\ ^\circ\mathrm C/\mathrm{PWM}.
$$

| Command | Predicted final temperature | Simulated final temperature |
|---:|---:|---:|
| $+25$ PWM | $33.50^\circ\mathrm C$ |  |
| $-25$ PWM | $16.25^\circ\mathrm C$ |  |
| $-50$ PWM | $10.50^\circ\mathrm C$ |  |

The heating and cooling changes are unequal because $\chi_h\ne\chi_c$.

| Check | Calculated value | Simulation value |
|---|---:|---:|
| $\chi_h=(T_{\mathrm{ss}}-22)/u$ |  | $0.46^\circ\mathrm C/\mathrm{PWM}$ |
| $\chi_c=(22-T_{\mathrm{ss}})/|u|$ |  | $0.23^\circ\mathrm C/\mathrm{PWM}$ |
| $r=\chi_h/\chi_c$ |  | 2.00 |

## 2. Runs using our measured values

Enter:

| Setting | Value |
|---|---:|
| $T_{\mathrm{amb}}$ | $22.0^\circ\mathrm C$ |
| $\chi_h$ | $0.4872^\circ\mathrm C/\mathrm{PWM}$ |
| $\chi_c$ | $0.20^\circ\mathrm C/\mathrm{PWM}$ |
| $\tau$ | $97\ \mathrm{s}$ |
| Voltage |  |
| Resistance | $1.50\ \Omega$ |
| $\Delta t$ |  |

| Run | Command | Predicted final temperature | Simulated final temperature | Measured final temperature | Difference or note |
|---|---:|---:|---:|---:|---|
| Heating | $+15$ PWM | $29.31^\circ\mathrm C$ |  |  |  |
| Cooling | $-130$ PWM | $-4.00^\circ\mathrm C$ |  |  |  |

Smaller $\Delta t$ used: ______ s  
Did the result change appreciably? ______

## 3. P-control runs

Select `p` and use a $30^\circ\mathrm C$ setpoint.

| $K_p$ | Predicted droop | Predicted final temperature | Predicted closed-loop time constant | Simulated result agrees? |
|---:|---:|---:|---:|:---:|
| 2 PWM/°C | $4.05^\circ\mathrm C$ | $25.95^\circ\mathrm C$ | $49.1\ \mathrm{s}$ |  |
| 10 PWM/°C | $1.36^\circ\mathrm C$ | $28.64^\circ\mathrm C$ | $16.5\ \mathrm{s}$ |  |

Increasing $K_p$ should reduce both droop and response time.
