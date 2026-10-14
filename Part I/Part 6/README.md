# Part 6: Add Integral Action in Simulation


1. **While $e>0$, why does $u_I$ continue to grow?**  
   The controller keeps adding the positive error to the integral state. Because $u_I=K_iq$, the integral contribution grows while positive error remains.

2. **As $T$ reaches the setpoint, why does $u_P$ approach zero?**  
   The proportional contribution is $u_P=K_pe$. As $T$ approaches $T_{\mathrm{set}}$, the error approaches zero, so $u_P$ also approaches zero.

3. **Why can $u_I$ remain nonzero when $e=0$?**  
   The integral stores the accumulated past error. When the current error becomes zero, the stored value remains and supplies the steady PWM needed to balance heat loss.

4. **After steady state, why does pressing Zero integral initially move the temperature away from the setpoint?**  
   Clearing the integral removes the PWM that was balancing passive heat loss. With insufficient TEC heating, the object initially moves back toward ambient temperature until new error rebuilds the controller output.
