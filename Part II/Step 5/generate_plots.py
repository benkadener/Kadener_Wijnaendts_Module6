"""Reproduce the six two-lump runs with a shared model and experimental timing."""
import os
import sys
import importlib.util
from pathlib import Path
from dataclasses import replace
import csv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ.setdefault('MPLCONFIGDIR', '/tmp/a3-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

model = load_module('tec_model', ROOT / 'Part I/Part 4/Lab_6_7_modeling_tec.py')
exp = load_module('experimental_analysis', ROOT / 'Part I/Part 7/analyze_goldilocks.py')
exp.OUTPUT_DIRECTORY = HERE
constants = model.constants_from_measurements(.20, .4872, 97., 12., 1.50)
base = model.ModelConfig(
    ambient_c=22., measured_cooling_chi_c_per_pwm=.20,
    measured_heating_chi_c_per_pwm=.4872, measured_tau_s=97.,
    total_capacitance_j_per_c=constants.total_capacitance_j_per_c,
    heat_loss_w_per_c=constants.heat_loss_w_per_c,
    tec_power_w_per_pwm=constants.cooling_power_w_per_pwm,
    heating_to_cooling_ratio=constants.heating_to_cooling_ratio,
    coupling_w_per_c=2., tec_capacitance_fraction=.35,
    dt_s=.05, pwm_limit=255., anti_windup=True,
)

def simulate(reference, kp, ki):
    initial = float(reference['temperature_C'][0])
    target = float(reference['setpoint_C'][0])
    config = replace(base, initial_c=initial, setpoint_c=target,
                     kp_pwm_per_c=kp, ki_pwm_per_c_s=ki)
    state = model.ModelState(time_s=0., tec_temperature_c=initial,
                             measured_temperature_c=initial, integral_error_c_s=0.)
    time = reference['time_s']
    temp, pwm = [], []
    for t in time:
        while state.time_s + config.dt_s <= t + 1e-9:
            model.advance_model(state, config, 'two_lump', 'pi' if ki else 'p')
        command = model.controller_command(state, config, 'two_lump', 'pi' if ki else 'p', advance_integral=False)[3]
        temp.append(state.measured_temperature_c)
        pwm.append(command)
    result = dict(reference)
    result.update(temperature_C=np.array(temp), applied_signed_pwm=np.array(pwm))
    result['mode'] = 'PI' if ki else 'P-only'
    result['ki_pwm_per_C_s'] = np.full(len(time), ki)
    result['kp_pwm_per_C'] = np.full(len(time), kp)
    return result, config

loaded = {}
readme = [
    'All six simulations use Tamb = 22 °C, χc = 0.20 and χh = 0.4872 °C/PWM, τ = 97 s, VTEC = 12 V (experimental voltage unconfirmed), RM = 1.50 Ω, G = 2 W/K, CT/C = 0.35, PWM limits ±255, Euler step 0.05 s, and conditional-integration anti-windup; the inferred C = %.4f J/K and H = %.4f W/K are fixed throughout.' % (base.total_capacitance_j_per_c, base.heat_loss_w_per_c),
    '',
    'Curves are regenerated with the supplied GUI model, not extracted from screenshots. Each direction starts with both lumps at the recorded first measured temperature and zero integral; directions are reset separately and displayed consecutively. The hidden TEC-side initial temperature is assumed. Experimental initial-condition differences and segment discontinuities are retained. Stability values below are local, unsaturated, direction-specific predictions.',
    '',
]
for index, (name, title, heat_file, cool_file) in enumerate(exp.CASES):
    refs = [exp.load_run(heat_file), exp.load_run(cool_file)]
    kp = [20,60,200,55,55,55][index]
    ki = [0,0,0,.08,.30,.80][index]
    pairs = [simulate(ref, kp, ki) for ref in refs]
    heating, cooling = [pair[0] for pair in pairs]
    loaded[name] = (heating, cooling)
    labels=[]
    for direction, (_, config) in zip(('Heating','Cooling'), pairs):
        if ki:
            critical = model.two_lump_pi_critical_integral_gain(config)
            labels.append(f'{direction}: Ki,crit={critical:.3f}, ρI={ki/critical:.3f}')
        else:
            labels.append(f'{direction}: ζ2L,P={model.two_lump_p_damping_ratio(config):.3f}')
    fig, axes=plt.subplots(2,1,figsize=(10,7),sharex=True,constrained_layout=True)
    offset=float(heating['time_s'][-1])+float(np.median(np.diff(heating['time_s'])))
    for data, shift, label in ((heating,0,'Heating'),(cooling,offset,'Cooling (reset)')):
        t=data['time_s']+shift
        axes[0].plot(t,data['temperature_C'],color='#d95f02',lw=1.6,label='Simulated measured Tm' if not shift else None)
        axes[0].plot(t,data['setpoint_C'],color='#008c95',ls='--',label='Setpoint' if not shift else None)
        axes[1].plot(t,data['applied_signed_pwm'],color='black',lw=1.3,label='Applied signed PWM' if not shift else None)
    # Match each experimental figure's automatic temperature and time limits.
    ref_t=np.concatenate((refs[0]['time_s'],refs[1]['time_s']+offset))
    ref_y=np.concatenate([r['temperature_C'] for r in refs]+[r['setpoint_C'] for r in refs])
    yrange=float(np.ptp(ref_y))
    axes[0].set_ylim(12, 38)
    axes[1].set_xlim(-.05*ref_t[-1],1.05*ref_t[-1])
    for ax in axes:
        ax.axvline(offset,color='.45',ls=':',label='Cooling segment (reset)' if ax is axes[0] else None)
        ax.grid(alpha=.25)
        ax.legend(fontsize=8)
    axes[0].set_ylabel('Output y: measured temperature (°C)')
    axes[1].set_ylabel('Input u: applied signed PWM')
    axes[1].set_xlabel('Elapsed time (s)')
    axes[1].set_ylim(-265,265)
    axes[1].axhline(0,color='.5',lw=.8)
    fig.suptitle(f'{title}: two-lump heating and cooling\nKp={kp:g}, Ki={ki:g}\n'+ '; '.join(labels),fontsize=11)
    fig.savefig(HERE/f'{name}.png',dpi=220)
    plt.close(fig)
    readme += [f'![{title}]({name}.png)', '',f'Kp = {kp:g}, Ki = {ki:g}; '+ '; '.join(labels)+'.','']
    for direction,data in zip(('heating','cooling'),(heating,cooling)):
        with (HERE/f'{name}_{direction}.csv').open('w',newline='') as f:
            writer=csv.writer(f)
            writer.writerow(['time_s','temperature_C','setpoint_C','applied_signed_pwm'])
            writer.writerows(zip(*(data[k] for k in ('time_s','temperature_C','setpoint_C','applied_signed_pwm'))))
# Reuse the experimental overlay's alignment and layout.
# Replace its experimental wording with an explicit simulation title.
# The helper closes figures, so temporarily intercept savefig to retitle it.
original_savefig=plt.Figure.savefig
def save_overlay(fig,*args,**kwargs):
    fig.suptitle('Two-lump Goldilocks simulations: heating followed by cooling',fontsize=15,fontweight='bold')
    for ax in fig.axes:
        if ax.get_ylabel().startswith('Output:'):
            ax.set_ylim(12,38)
    return original_savefig(fig,*args,**kwargs)
plt.Figure.savefig=save_overlay
exp.plot_combined_overlay(loaded)
plt.Figure.savefig=original_savefig
readme += ['![Goldilocks overlay](goldilocks_overlay.png)', '',
           'Overlay directions are truncated to the shortest experimental heating and cooling durations so all transitions and endpoints align, as in Part I. All simulation temperature axes use 12–38 °C to show the full overshoot and undershoot; experimental figure temperature axes will need the same range in the final comparison assembly.', '',
           'Regenerate: `python3 "Part II/Step 5/generate_plots.py"`.']
readme += [
    '',
    '### Growth followed by saturation',
    '',
    'A separate reproduction of the Step 4 demonstration uses Tamb = T0 = 29 °C, Tset = 30 °C, C = 100 J/K, CT/C = 0.50, G = 2 W/K, H = 1.14 W/K, Pu,c = 0.26 W/PWM, r = 2, Kp = 10, Ki = 3, and anti-windup on. Ki,crit = 1.253, so ρI = 2.394. Before approximately 357.5 s, oscillations grow while the command is unsaturated: evidence of linear instability. Applied PWM first reaches a limit at approximately 357.5 s. Later clipping at ±255 limits the oscillation amplitude; bounded oscillation reflects the nonlinear actuator limit, not restored linear stability. This timing comes from the supplied Euler model at Δt = 0.05 s, not a measurement. No extra plot is included.',
    '',
    '### PI predictions and resets',
    '',
    'For Ki = 0.08, 0.30, and 0.80 at Kp = 55, heating ρI increases from 0.016 to 0.062 to 0.165; cooling ρI increases from 0.016 to 0.059 to 0.157. All predict decaying oscillations, not marginal or unstable behavior. Larger ρI moves toward the stability boundary, but all three remain far below 1. Each segment resets the integral to zero with anti-windup enabled; captions give Kp, Ki, Ki,crit, and ρI.',
    '',
    '### 1. Which simulations best match the experiments?',
    '',
    'No case reproduces all three response measures. Low-P heating matches rise time closely (17.53 s simulated versus 17.54 s experimental), but overpredicts overshoot (21.02% versus 0.12%). Low-P cooling gives the closest settling time (58.21 s versus 60.54 s). Low-PI has the smallest overall rise/settling discrepancies among the PI cases, but remains a poor quantitative match: heating rise time is 17.90 s versus 5.71 s and settling is 83.16 s versus 19.42 s. Metrics use the Part I 10–90% rise and ±2% settling definitions around the finite-record final temperature.',
    '',
    '### 2. How do the P gains organize the responses?',
    '',
    'The critical-damping gain Kp,crit is 3.15 PWM/°C for heating and 7.67 PWM/°C for cooling. All three experimental gains (20, 60, 200) exceed these values. Increasing Kp reduces heating ζ from 0.486 to 0.290 to 0.160 and cooling ζ from 0.712 to 0.442 to 0.249: all are locally stable underdamped P cases. Kp,crit marks critical damping, not a P instability boundary. PWM saturation means faster local dynamics do not guarantee monotonically shorter measured rise times.',
    '',
    '### 3. How does increasing ρI organize the PI responses?',
    '',
    'All three PI simulations are stable underdamped, with decaying oscillations. Higher Ki increases ρI and strengthens integral action, but saturation makes the initial responses similar and settling need not vary monotonically. High-PI heating takes 125.32 s to settle in simulation versus 83.16 s for low PI. None of these retained gains reaches ρI = 1; marginal and unstable behavior belong to the preliminary sweep.',
    '',
    '### 4. Agreement, disagreement, and gain choice',
    '',
    'Agreement: both experiment and simulation show overshoot at larger gains and finite heating/cooling asymmetry. Disagreement: simulated high-P heating settles in about 80.33 s, while experimental high-P heating has sustained oscillation and no measured settling time. The positive-parameter, fixed-direction linear two-lump P model cannot produce sustained or growing oscillations; persistent experimental ringing contradicts that model under its assumptions and points to omitted delay, actuator dynamics, or additional thermal states. The switched, saturated simulation shown here still produces decaying oscillations.',
    '',
    'Experimental low/medium-P responses are approximately stable non-oscillatory or have a single overshoot; high-P heating is sustained-oscillatory over the recorded interval, while high-P cooling settles. Sustained oscillation in a finite, saturated record does not establish ideal marginal stability. The PI records appear stable with decaying transients, although low-PI cooling starts at only 30.58 °C and its finite duration limits conclusions about zero final error. No recorded case establishes unbounded instability. All six simulations have decaying underdamped transients; none demonstrates marginal stability or growth.',
    '',
    'A provisional experimental compromise is P Kp = 60: fast heating without the sustained oscillation at 200. For PI, Kp = 55 and Ki = 0.30 is a reasonable middle choice that reduces the residual error of Ki = 0.08 without choosing the most aggressive integral action. Ki = 0.80 does not shorten the measured heating settling time relative to 0.30 (29.34 s versus 27.99 s). This is a practical candidate, not a model-validated optimum; unmatched initial conditions, substantial simulation error, and the lack of a stated acceptable-error tolerance prevent a definitive ranking.',
]
(HERE/'README.md').write_text('\n'.join(readme)+'\n')
print('Created six case plots, overlay, source CSVs, and README.')
