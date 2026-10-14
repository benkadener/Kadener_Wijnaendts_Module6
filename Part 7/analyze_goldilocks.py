"""Create the six A3 experimental Goldilocks plots and high-gain metrics."""

import csv
import os
from collections import Counter
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(SCRIPT_DIRECTORY / ".mplconfig"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DATA_DIRECTORY = SCRIPT_DIRECTORY / "run_data"
OUTPUT_DIRECTORY = SCRIPT_DIRECTORY / "analysis_output"

# One figure is produced for each pair of heating and cooling files.
CASES = [
	("01_p_low", "P — low gain", "Low_kp_Heating.csv", "Low_kp_Cooling.csv"),
	("02_p_medium", "P — medium gain", "Medium_kp_Heating.csv", "Medium_kp_Cooling.csv"),
	("03_p_high", "P — high gain", "High_kp_Heating.csv", "High_kp_Cooling.csv"),
	("04_pi_low", "PI — low integral gain", "Low_ki_Heating.csv", "Low_ki_Cooling.csv"),
	("05_pi_medium", "PI — medium integral gain", "Medium_ki_Heating.csv", "Medium_ki_Cooling.csv"),
	("06_pi_high", "PI — high integral gain", "High_ki_Heating.csv", "High_ki_Cooling.csv"),
]

NUMERIC_COLUMNS = (
	"time_s",
	"temperature_C",
	"setpoint_C",
	"kp_pwm_per_C",
	"ki_pwm_per_C_s",
	"applied_signed_pwm",
)


def load_run(filename):
	"""Load one CSV and retain its dominant controller/gain/setpoint block."""
	path = DATA_DIRECTORY / filename
	with path.open(newline="") as csv_file:
		rows = list(csv.DictReader(csv_file))
	if not rows:
		raise ValueError(f"{path} contains no measurements")

	keys = [
		(
			row["controller_mode"],
			row["kp_pwm_per_C"],
			row["ki_pwm_per_C_s"],
			row["setpoint_C"],
		)
		for row in rows
	]
	dominant_key, dominant_count = Counter(keys).most_common(1)[0]
	rows = [row for row, key in zip(rows, keys) if key == dominant_key]
	if dominant_count < 0.8 * len(keys):
		print(f"Warning: {filename} contains substantial mixed settings; using {dominant_key}")

	data = {name: np.array([float(row[name]) for row in rows]) for name in NUMERIC_COLUMNS}
	data["time_s"] = data["time_s"] - data["time_s"][0]
	data["mode"] = dominant_key[0]
	data["source"] = filename
	return data


def smooth(values, points=9):
	"""Return a centered moving average without changing the array length."""
	points = max(1, min(int(points), len(values)))
	if points == 1:
		return values.copy()
	left = points // 2
	right = points - 1 - left
	padded = np.pad(values, (left, right), mode="edge")
	return np.convolve(padded, np.ones(points) / points, mode="valid")


def crossing_time(time, progress, threshold):
	"""Find the first threshold crossing and linearly interpolate its time."""
	indices = np.flatnonzero(progress >= threshold)
	if not len(indices):
		return np.nan
	i = int(indices[0])
	if i == 0 or progress[i] == progress[i - 1]:
		return float(time[i])
	fraction = (threshold - progress[i - 1]) / (progress[i] - progress[i - 1])
	return float(time[i - 1] + fraction * (time[i] - time[i - 1]))


def oscillation_period(time, temperature, final_temperature, direction, amplitude):
	"""Estimate a period from successive same-direction peaks after the step."""
	deviation = direction * (temperature - final_temperature)
	threshold = max(0.05, 0.02 * amplitude)
	candidates = []
	for i in range(1, len(deviation) - 1):
		if deviation[i - 1] < deviation[i] >= deviation[i + 1] and deviation[i] > threshold:
			candidates.append(i)

	# Retain the strongest peak in each five-second neighborhood.
	peaks = []
	for index in candidates:
		if not peaks or time[index] - time[peaks[-1]] >= 5.0:
			peaks.append(index)
		elif deviation[index] > deviation[peaks[-1]]:
			peaks[-1] = index
	if len(peaks) < 2:
		return np.nan
	return float(np.median(np.diff(time[peaks])))


def calculate_metrics(data):
	"""Calculate the required metrics using 10–90% rise and ±2% settling."""
	time = data["time_s"]
	temperature = smooth(data["temperature_C"])
	# These recorded files begin at the commanded step, and the high-gain cases
	# move within about one second. Use only the first five samples for the
	# initial value, then a longer late-time window for the settled value.
	n_initial = min(5, len(temperature))
	n_final = max(20, min(len(temperature) // 10, 100))
	initial = float(np.median(data["temperature_C"][:n_initial]))
	final = float(np.median(temperature[-n_final:]))
	setpoint = float(np.median(data["setpoint_C"][-n_final:]))
	change = final - initial
	amplitude = abs(change)
	if amplitude < 0.1:
		raise ValueError(f"Temperature change in {data['source']} is too small")
	direction = 1.0 if change > 0 else -1.0
	progress = direction * (temperature - initial)

	t10 = crossing_time(time, progress, 0.10 * amplitude)
	t90 = crossing_time(time, progress, 0.90 * amplitude)
	rise_time = t90 - t10 if np.isfinite(t10) and np.isfinite(t90) else np.nan

	peak_progress = float(np.max(progress))
	overshoot = max(0.0, 100.0 * (peak_progress - amplitude) / amplitude)

	settling_band = 0.02 * amplitude
	outside = np.flatnonzero(np.abs(temperature - final) > settling_band)
	if not len(outside):
		settling_time = 0.0
	elif outside[-1] + 1 < len(time):
		settling_time = float(time[outside[-1] + 1])
	else:
		settling_time = np.nan

	period = oscillation_period(time, temperature, final, direction, amplitude)
	return {
		"initial_temperature_C": initial,
		"final_temperature_C": final,
		"rise_time_s": rise_time,
		"percent_overshoot": overshoot,
		"settling_time_s": settling_time,
		"steady_state_error_C": setpoint - final,
		"oscillation_period_s": period,
	}


def setting_label(data):
	label = f"{data['mode']}, Kp={data['kp_pwm_per_C'][0]:g} PWM/°C"
	if data["mode"] == "PI":
		label += f", Ki={data['ki_pwm_per_C_s'][0]:g} PWM/(°C·s)"
	return label


def plot_case(output_name, title, heating, cooling):
	"""Create one required plot with heating then cooling in two panels."""
	heating_time = heating["time_s"]
	cooling_time = cooling["time_s"]
	if len(heating_time) > 1:
		sample_interval = float(np.median(np.diff(heating_time)))
	else:
		sample_interval = 0.1
	cooling_time = cooling_time + heating_time[-1] + sample_interval
	transition_time = float(cooling_time[0])

	time = np.concatenate((heating_time, cooling_time))
	temperature = np.concatenate((heating["temperature_C"], cooling["temperature_C"]))
	setpoint = np.concatenate((heating["setpoint_C"], cooling["setpoint_C"]))
	applied_pwm = np.concatenate((heating["applied_signed_pwm"], cooling["applied_signed_pwm"]))

	fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
	axes[0].plot(time, temperature, color="#d95f02", lw=1.6, label="Measured T")
	axes[0].plot(time, setpoint, color="#008c95", lw=1.5, ls="--", label="Setpoint")
	axes[0].axvline(transition_time, color="0.45", lw=1, ls=":", label="Cooling step")
	axes[0].set_ylabel("Output y: measured temperature (°C)")
	axes[0].legend(loc="best")
	axes[0].grid(alpha=0.25)

	axes[1].plot(time, applied_pwm, color="black", lw=1.3, label="Applied signed PWM")
	axes[1].axhline(0, color="0.5", lw=0.8)
	axes[1].axvline(transition_time, color="0.45", lw=1, ls=":")
	axes[1].set_ylabel("Input u: applied signed PWM")
	axes[1].set_xlabel("Elapsed time (s)")
	axes[1].set_ylim(-265, 265)
	axes[1].legend(loc="best")
	axes[1].grid(alpha=0.25)

	fig.suptitle(f"{title}: heating and cooling\n{setting_label(heating)}", fontsize=14, fontweight="bold")
	path = OUTPUT_DIRECTORY / f"{output_name}.png"
	fig.savefig(path, dpi=220)
	plt.close(fig)
	print(f"Created {path}")


def plot_overlay(direction_name, direction_index, loaded):
	"""Overlay low-, medium-, and high-gain traces in the reference format."""
	fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex="col", constrained_layout=True)
	groups = (
		("P control", ("01_p_low", "02_p_medium", "03_p_high"), "$K_p$"),
		("PI control", ("04_pi_low", "05_pi_medium", "06_pi_high"), "$K_i$"),
	)
	colors = ("#56B4E9", "#0072B2", "#6A3D9A")
	levels = ("Low", "Medium", "High")
	all_case_names = tuple(case_name for _, case_names, _ in groups for case_name in case_names)
	common_end_time = min(loaded[case_name][direction_index]["time_s"][-1] for case_name in all_case_names)

	for column, (controller_title, case_names, varied_gain) in enumerate(groups):
		for color, level, case_name in zip(colors, levels, case_names):
			data = loaded[case_name][direction_index]
			time = data["time_s"]
			keep = time <= common_end_time
			if data["mode"] == "PI":
				gain_text = f"Ki={data['ki_pwm_per_C_s'][0]:g}"
			else:
				gain_text = f"Kp={data['kp_pwm_per_C'][0]:g}"
			label = f"{level} ({gain_text})"
			axes[0, column].plot(time[keep], data["temperature_C"][keep], color=color, lw=1.6, label=label)
			axes[1, column].plot(time[keep], data["applied_signed_pwm"][keep], color=color, lw=1.3, label=label)

		setpoint_data = loaded[case_names[0]][direction_index]
		setpoint_keep = setpoint_data["time_s"] <= common_end_time
		axes[0, column].plot(
			setpoint_data["time_s"][setpoint_keep],
			setpoint_data["setpoint_C"][setpoint_keep],
			color="black",
			lw=1.2,
			ls="--",
			label="Setpoint",
		)
		axes[0, column].set_title(f"{controller_title}: varying {varied_gain}")
		axes[0, column].set_ylabel("Measured temperature (°C)")
		axes[0, column].legend(loc="best", fontsize=8)
		axes[0, column].grid(alpha=0.25)
		axes[1, column].axhline(0, color="0.5", lw=0.8)
		axes[1, column].set_ylabel("Applied signed PWM")
		axes[1, column].set_xlabel("Elapsed time (s)")
		axes[1, column].set_ylim(-265, 265)
		axes[1, column].set_xlim(0, common_end_time)
		axes[1, column].legend(loc="best", fontsize=8)
		axes[1, column].grid(alpha=0.25)

	fig.suptitle(f"Experimental Goldilocks comparison — {direction_name}", fontsize=15, fontweight="bold")
	path = OUTPUT_DIRECTORY / f"goldilocks_overlay_{direction_name.lower()}.png"
	fig.savefig(path, dpi=220)
	plt.close(fig)
	print(f"Created {path}")


def combine_heating_and_cooling(heating, cooling, heating_end=None, cooling_end=None):
	"""Join separately recorded directions into one continuous response."""
	heating_keep = np.ones(len(heating["time_s"]), dtype=bool)
	cooling_keep = np.ones(len(cooling["time_s"]), dtype=bool)
	if heating_end is not None:
		heating_keep = heating["time_s"] <= heating_end
	if cooling_end is not None:
		cooling_keep = cooling["time_s"] <= cooling_end
	heating_time = heating["time_s"][heating_keep]
	sample_interval = float(np.median(np.diff(heating_time))) if len(heating_time) > 1 else 0.1
	cooling_time = cooling["time_s"][cooling_keep] + heating_time[-1] + sample_interval
	return {
		"time_s": np.concatenate((heating_time, cooling_time)),
		"temperature_C": np.concatenate((heating["temperature_C"][heating_keep], cooling["temperature_C"][cooling_keep])),
		"setpoint_C": np.concatenate((heating["setpoint_C"][heating_keep], cooling["setpoint_C"][cooling_keep])),
		"applied_signed_pwm": np.concatenate((heating["applied_signed_pwm"][heating_keep], cooling["applied_signed_pwm"][cooling_keep])),
		"mode": heating["mode"],
		"kp": float(heating["kp_pwm_per_C"][0]),
		"ki": float(heating["ki_pwm_per_C_s"][0]),
	}


def plot_combined_overlay(loaded):
	"""Create one reference-style four-panel overlay of all six responses."""
	common_heating_end = min(directions[0]["time_s"][-1] for directions in loaded.values())
	common_cooling_end = min(directions[1]["time_s"][-1] for directions in loaded.values())
	combined = {
		name: combine_heating_and_cooling(
			*directions,
			heating_end=common_heating_end,
			cooling_end=common_cooling_end,
		)
		for name, directions in loaded.items()
	}
	groups = (
		("P control", ("01_p_low", "02_p_medium", "03_p_high"), "$K_p$"),
		("PI control", ("04_pi_low", "05_pi_medium", "06_pi_high"), "$K_i$"),
	)
	colors = ("#56B4E9", "#0072B2", "#6A3D9A")
	levels = ("Low", "Medium", "High")
	common_end_time = min(data["time_s"][-1] for data in combined.values())
	fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex="col", constrained_layout=True)

	for column, (controller_title, case_names, varied_gain) in enumerate(groups):
		for color, level, case_name in zip(colors, levels, case_names):
			data = combined[case_name]
			keep = data["time_s"] <= common_end_time
			gain_text = f"Ki={data['ki']:g}" if data["mode"] == "PI" else f"Kp={data['kp']:g}"
			label = f"{level} ({gain_text})"
			axes[0, column].plot(data["time_s"][keep], data["temperature_C"][keep], color=color, lw=1.5, label=label)
			axes[1, column].plot(data["time_s"][keep], data["applied_signed_pwm"][keep], color=color, lw=1.3, label=label)

		reference = combined[case_names[0]]
		keep = reference["time_s"] <= common_end_time
		axes[0, column].plot(reference["time_s"][keep], reference["setpoint_C"][keep], color="black", lw=1.2, ls="--", label="Setpoint")
		axes[0, column].set_title(f"{controller_title}: varying {varied_gain}")
		axes[0, column].set_ylabel("Output: measured temperature (°C)")
		axes[0, column].legend(loc="best", fontsize=8)
		axes[0, column].grid(alpha=0.25)
		axes[1, column].axhline(0, color="0.5", lw=0.8)
		axes[1, column].set_ylabel("Input: applied signed PWM")
		axes[1, column].set_xlabel("Elapsed time (s)")
		axes[1, column].set_ylim(-265, 265)
		axes[1, column].set_xlim(0, common_end_time)
		axes[1, column].legend(loc="best", fontsize=8)
		axes[1, column].grid(alpha=0.25)

	fig.suptitle("Experimental Goldilocks plots: heating followed by cooling", fontsize=15, fontweight="bold")
	path = OUTPUT_DIRECTORY / "goldilocks_overlay.png"
	fig.savefig(path, dpi=220)
	plt.close(fig)
	print(f"Created {path}")


def format_metric(value):
	return "N/A" if not np.isfinite(value) else f"{value:.2f}"


def write_metrics(metric_rows):
	fieldnames = ["case", "direction", "source_file", "initial_temperature_C", "final_temperature_C", "rise_time_s", "percent_overshoot", "settling_time_s", "steady_state_error_C", "oscillation_period_s"]
	csv_path = OUTPUT_DIRECTORY / "high_gain_metrics.csv"
	with csv_path.open("w", newline="") as csv_file:
		writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
		writer.writeheader()
		writer.writerows(metric_rows)

	markdown_path = OUTPUT_DIRECTORY / "high_gain_metrics.md"
	with markdown_path.open("w") as output:
		output.write("# High-Gain Step-Response Metrics\n\n")
		output.write("Rise time uses 10–90% of the measured final change. Settling time uses a ±2% band around the measured final temperature.\n\n")
		output.write("| Case | Direction | Rise time (s) | Overshoot (%) | Settling time (s) | Steady-state error (°C) | Oscillation period (s) |\n")
		output.write("|---|---|---:|---:|---:|---:|---:|\n")
		for row in metric_rows:
			output.write(
				f"| {row['case']} | {row['direction']} | {format_metric(row['rise_time_s'])} | "
				f"{format_metric(row['percent_overshoot'])} | {format_metric(row['settling_time_s'])} | "
				f"{format_metric(row['steady_state_error_C'])} | {format_metric(row['oscillation_period_s'])} |\n"
			)
	print(f"Created {csv_path}")
	print(f"Created {markdown_path}")


def main():
	OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
	# Remove plots from earlier analyses so this folder contains exactly the six
	# experimental figures required for Question 2.
	for old_plot in OUTPUT_DIRECTORY.glob("*.png"):
		old_plot.unlink()
	loaded = {}
	for output_name, title, heating_file, cooling_file in CASES:
		heating = load_run(heating_file)
		cooling = load_run(cooling_file)
		loaded[output_name] = (heating, cooling)
		plot_case(output_name, title, heating, cooling)

	plot_combined_overlay(loaded)

	metric_rows = []
	for case_name, output_name in (("High P", "03_p_high"), ("High PI", "06_pi_high")):
		for direction, data in zip(("Upward", "Downward"), loaded[output_name]):
			row = {"case": case_name, "direction": direction, "source_file": data["source"]}
			row.update(calculate_metrics(data))
			metric_rows.append(row)
	write_metrics(metric_rows)


if __name__ == "__main__":
	main()
