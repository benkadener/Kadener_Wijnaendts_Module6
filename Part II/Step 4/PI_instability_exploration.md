# Step 4: PI instability and the PWM limit

This is an explanation of the existing Step 4 run; it does not add or change a
plot.

## What the plots show

The run uses the two-lump model with PI control. In the displayed settings,
$K_p=10$ PWM/°C, $K_i=3$ PWM/(°C·s), and the actuator limit is
$u_{\max}=255$ PWM. The stability indicator reports
$K_i/K_{i,\mathrm{crit}}=2.394$, which is greater than one.

1. **Growing oscillation envelope (before clipping):** At the start of the
   response, compare successive temperature peaks and troughs while the
   requested command is still inside the PWM limits. Their increasing
   deviation from the setpoint is the signature of a growing oscillation. In
   the simulation with the displayed settings, the first temperature maximum
   is around 36 s and the first minimum around 85 s; the response reaches its
   next maximum around 120 s. These are approximate model times, not extra
   measurements from the screenshot.
2. **First actuator limit:** The applied command first reaches the negative
   limit, approximately **−255 PWM at 120 s**. The controller's unsaturated
   requested command has exceeded what the actuator can apply.
3. **Later bounded oscillation:** After clipping begins, the temperature
   continues to oscillate rather than diverging. In the displayed run, later
   cycles are roughly 80–85 s apart, with measured-temperature extrema near
   22.4°C and 40.9°C. The command repeatedly flattens at +255 or −255 PWM.

## Why the behavior changes

Before saturation, the PI controller and two-lump thermal model behave
approximately like a linear feedback system. Here the integral gain is above
the calculated stability boundary, so the unsaturated linear system has a
growing oscillatory mode: each cycle tends to increase the oscillation
envelope.

The actuator is not linear once the requested command exceeds its available
range. The applied PWM is clipped to $[-255,255]$, limiting the heat or
cooling power the model can receive. That nonlinear cap prevents the
temperature oscillation from growing without bound and produces the later
bounded, repeating behavior. The bounded cycles therefore do **not** show
that the linear controller is stable; they show the effect of actuator
saturation on an unstable linear response.
