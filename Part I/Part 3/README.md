# Part 3: Estimate the Thermal Time Constant

The Module 5 $K_p=0.5$ heating run was used. After P-only control was enabled, the integer command remained at PWM 3, so this run approximates a constant-command temperature step. The Module 5 Arduino averaged 1000 raw thermistor readings for every reported temperature.

From the Module 5 `temperature_measurements.csv` file:

- The PWM step from 0 to 3 began at $t_{\mathrm{step}}=8.80\ \mathrm{s}$.
- The mean of the last 20 measurements before the step was $T_{\mathrm{initial}}=23.23^\circ\mathrm C$.
- The mean temperature during the final 60 seconds was used as the approximate final temperature: $T_{\mathrm{final}}=24.21^\circ\mathrm C$.

The 63% temperature is

$$
\begin{aligned}
T_{63}
&=T_{\mathrm{initial}}+0.63(T_{\mathrm{final}}-T_{\mathrm{initial}})\\
&=23.23+0.63(24.21-23.23)\\
&=23.85^\circ\mathrm C.
\end{aligned}
$$

The trace first reached $23.85^\circ\mathrm C$ at approximately

$$
t_{63}=105.86\ \mathrm{s}.
$$

Therefore, the estimated thermal time constant is

$$
\boxed{
\tau=t_{63}-t_{\mathrm{step}}
=105.86-8.80
=97.06\ \mathrm{s}
\approx97\ \mathrm{s}
}.
$$

Changing the final-temperature averaging interval from 30 to 90 seconds changes the estimate from approximately 100 to 94 seconds. A reasonable estimate, including uncertainty in the settled temperature and crossing time, is

$$
\boxed{\tau\approx97\pm5\ \mathrm{s}}.
$$

This measurement determines the ratio $C/H$ because $\tau=C/H$; it does not determine $C$ and $H$ separately.
