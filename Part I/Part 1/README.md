# Part 1: Numerical Check

Using the Module 5 heating run with

$$
\chi_{T,u}=0.4872\ \frac{^\circ\mathrm C}{\text{PWM count}},\qquad
T_{\mathrm{amb}}=22.0^\circ\mathrm C,\qquad
T_{\mathrm{set}}=30.0^\circ\mathrm C,\qquad
chose: K_p=2.00\ \frac{\text{PWM counts}}{^\circ\mathrm C},
$$

the predicted droop is

$$
T_{\mathrm{set}}-T
=\frac{T_{\mathrm{set}}-T_{\mathrm{amb}}}
{1+\chi_{T,u}K_p}
=\frac{30.0-22.0}{1+(0.4872)(2.00)}
=4.05^\circ\mathrm C.
$$

Therefore, the predicted settled temperature is

$$
T=30.0-4.05=25.95^\circ\mathrm C.
$$

The measured Module 5 settled temperature was $26.27^\circ\mathrm C$, corresponding to a measured droop of

$$
30.0-26.27=3.73^\circ\mathrm C.
$$

The measured droop was $0.32^\circ\mathrm C$ smaller than the predicted droop. One physical reason for the difference is that the real TEC susceptibility changes somewhat with temperature, whereas the model assumes the constant value $\chi_{T,u}=0.4872\ ^\circ\mathrm C/\text{PWM count}$.
