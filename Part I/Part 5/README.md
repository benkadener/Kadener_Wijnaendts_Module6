# Part 5: One-Lump P Transient and Its Limit

Use the Module 5 $K_p=60$ high-gain trace.

## Model prediction

The one-lump P-control response is

$$
T(t)=T_{\mathrm{ss}}+[T(0)-T_{\mathrm{ss}}]e^{-t/\tau_{\mathrm{cl}}},
\qquad
\tau_{\mathrm{cl}}=\frac{\tau}{1+\chi_hK_p}.
$$

Using $T_{\mathrm{amb}}=22^\circ\mathrm C$, $T_{\mathrm{set}}=30^\circ\mathrm C$, $\chi_h=0.4872^\circ\mathrm C/\mathrm{PWM}$, $\tau=97\ \mathrm{s}$, and $K_p=60\ \mathrm{PWM}/^\circ\mathrm C$:

$$
L=\chi_hK_p=(0.4872)(60)=29.232,
$$

$$
\text{predicted droop}=\frac{30-22}{1+29.232}=0.265^\circ\mathrm C,
$$

$$
T_{\mathrm{ss,predicted}}=30-0.265=29.74^\circ\mathrm C,
$$

$$
\tau_{\mathrm{cl}}=\frac{97}{1+29.232}=3.21\ \mathrm{s}.
$$

## Compare with the experimental trace

| Quantity | Model prediction | Module 5 trace |
|---|---:|---:|
| Late-time temperature $T_{\mathrm{ss}}$ | $29.74^\circ\mathrm C$ | $29.76^\circ\mathrm C$ |
| First peak temperature | No peak | About $31.5^\circ\mathrm C$ |
| First overshoot above $T_{\mathrm{ss}}$ | $0^\circ\mathrm C$ | About $31.5-29.76=1.74^\circ\mathrm C$ |
| PWM saturation? | Model assumes none | Yes, briefly at 255 PWM |


## Explanation

The one-lump model has one real, negative eigenvalue:

$$
\lambda=-\frac{H+P_uK_p}{C}.
$$

It therefore predicts a monotonic exponential approach to steady state. It cannot cross $T_{\mathrm{ss}}$, overshoot, or oscillate.

The experimental $K_p=60$ trace crosses its steady-state temperature, overshoots, and then settles. The steady-state prediction is accurate, but the one-lump model does not describe the transient response. A physical reason is thermal lag between the TEC and the block/thermistor. These regions store heat separately, so a two-lump model is needed. Initial PWM saturation may also affect the measured transient.
