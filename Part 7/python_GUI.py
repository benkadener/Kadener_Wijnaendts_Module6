"""Display Arduino temperature measurements in a rolling strip chart."""

import csv
import re
import sys
from collections import deque

import pyqtgraph as pg
import serial
from PySide6 import QtCore, QtGui, QtWidgets


# ---------- Settings to change before running ----------
SERIAL_PORT = "/dev/cu.usbmodem101"  # Change to your Arduino's serial port
BAUD_RATE = 9600
WINDOW_DURATION_SECONDS = 120.0
UPDATE_INTERVAL_MILLISECONDS = 100
CSV_FILENAME = "temperature_measurements.csv"
INITIAL_SETPOINT_C = 32.5
INITIAL_PROPORTIONAL_GAIN = 1.0
INITIAL_INTEGRAL_GAIN = 0.08
PWM_LIMIT = 255


# This matches the serial line printed by the Part 3 Arduino sketch.
MEASUREMENT_LINE = re.compile(
	r"^Temperature \(C\):\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)),\s*"
	r"Time \(s\):\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)),\s*"
	r"PWM:\s*(\d+),\s*Heat/Cool:\s*([01])\s*$"
)


def parse_measurement(line):
	"""Return time, temperature, PWM, and direction, or None if malformed."""
	match = MEASUREMENT_LINE.fullmatch(line.strip())
	if match is None:
		return None

	temperature = float(match.group(1))
	time_seconds = float(match.group(2))
	pwm = int(match.group(3))
	heat_cool = int(match.group(4))

	return time_seconds, temperature, pwm, heat_cool


def calculate_p_control(setpoint, temperature, gain):
	"""Return temperature error, signed output, PWM magnitude, and direction."""
	error = setpoint - temperature
	signed_pwm = gain * error
	direction = "HEAT" if signed_pwm >= 0 else "COOL"
	pwm = max(0, min(255, int(round(abs(signed_pwm)))))
	return error, signed_pwm, pwm, direction


class TemperatureWindow(QtWidgets.QMainWindow):
	"""Read Arduino measurements and provide manual serial controls."""

	def __init__(self):
		super().__init__()
		self.setWindowTitle("TEC Temperature")

		# Keep the rolling chart data separate from the CSV output values.
		self.times = deque()
		self.temperatures = deque()
		self.setpoints = deque()
		self.errors = deque()
		self.signed_pwms = deque()
		self.proportional_pwms = deque()
		self.integral_pwms = deque()
		self.requested_pwms = deque()
		self.serial_buffer = b""
		self.latest_temperature = None
		self.last_measurement_time = None
		self.setpoint = INITIAL_SETPOINT_C
		self.proportional_gain = INITIAL_PROPORTIONAL_GAIN
		self.integral_gain = INITIAL_INTEGRAL_GAIN
		self.integral_error = 0.0
		self.proportional_output = 0.0
		self.integral_output = 0.0
		self.requested_output = 0.0
		self.applied_output = 0.0

		# Create the manual controls and the live values shown above the plots.
		controls = QtWidgets.QGroupBox("Manual controls")
		controls_layout = QtWidgets.QGridLayout(controls)

		self.direction_switch = QtWidgets.QCheckBox("HEAT")
		self.direction_switch.setChecked(True)
		self.direction_switch.toggled.connect(self.direction_changed)
		controls_layout.addWidget(QtWidgets.QLabel("Direction"), 0, 0)
		controls_layout.addWidget(self.direction_switch, 0, 1)

		self.pwm_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
		self.pwm_slider.setRange(0, 255)
		self.pwm_slider.setValue(0)
		self.pwm_slider.valueChanged.connect(self.slider_changed)
		controls_layout.addWidget(QtWidgets.QLabel("PWM"), 1, 0)
		controls_layout.addWidget(self.pwm_slider, 1, 1)

		self.pwm_input = QtWidgets.QLineEdit("0")
		self.pwm_input.setValidator(QtGui.QIntValidator(0, 255, self))
		self.pwm_input.setMaximumWidth(80)
		self.pwm_input.editingFinished.connect(self.text_pwm_changed)
		controls_layout.addWidget(self.pwm_input, 1, 2)

		self.control_mode = QtWidgets.QComboBox()
		self.control_mode.addItems(["Manual", "P-only", "PI"])
		self.control_mode.currentTextChanged.connect(self.control_mode_changed)
		controls_layout.addWidget(QtWidgets.QLabel("Controller"), 2, 0)
		controls_layout.addWidget(self.control_mode, 2, 1)

		self.setpoint_input = QtWidgets.QLineEdit(str(INITIAL_SETPOINT_C))
		self.setpoint_input.setValidator(QtGui.QDoubleValidator(30.0, 35.0, 2, self))
		self.setpoint_input.setMaximumWidth(80)
		self.setpoint_input.editingFinished.connect(self.setpoint_changed)
		controls_layout.addWidget(QtWidgets.QLabel("Setpoint (30-35 C)"), 2, 2)
		controls_layout.addWidget(self.setpoint_input, 2, 3)

		self.gain_input = QtWidgets.QLineEdit(str(INITIAL_PROPORTIONAL_GAIN))
		self.gain_input.setValidator(QtGui.QDoubleValidator(0.0, 1000.0, 2, self))
		self.gain_input.setMaximumWidth(80)
		self.gain_input.editingFinished.connect(self.gain_changed)
		controls_layout.addWidget(QtWidgets.QLabel("Kp (PWM/C)"), 3, 0)
		controls_layout.addWidget(self.gain_input, 3, 1)

		self.integral_gain_input = QtWidgets.QLineEdit(str(INITIAL_INTEGRAL_GAIN))
		self.integral_gain_input.setValidator(
			QtGui.QDoubleValidator(0.0, 1000.0, 4, self)
		)
		self.integral_gain_input.setMaximumWidth(80)
		self.integral_gain_input.editingFinished.connect(self.integral_gain_changed)
		self.integral_gain_input.setEnabled(False)
		controls_layout.addWidget(QtWidgets.QLabel("Ki (PWM/(C s))"), 3, 2)
		controls_layout.addWidget(self.integral_gain_input, 3, 3)

		self.zero_integral_button = QtWidgets.QPushButton("Zero integral")
		self.zero_integral_button.clicked.connect(self.zero_integral)
		controls_layout.addWidget(self.zero_integral_button, 4, 0, 1, 2)

		self.temperature_value = QtWidgets.QLabel("-- C")
		self.pwm_value = QtWidgets.QLabel("--")
		self.direction_value = QtWidgets.QLabel("--")
		self.time_value = QtWidgets.QLabel("-- s")
		self.error_value = QtWidgets.QLabel("-- C")
		self.proportional_pwm_value = QtWidgets.QLabel("--")
		self.integral_pwm_value = QtWidgets.QLabel("--")
		self.requested_pwm_value = QtWidgets.QLabel("--")
		self.applied_pwm_value = QtWidgets.QLabel("--")
		live_values = QtWidgets.QFormLayout()
		live_values.addRow("Temperature", self.temperature_value)
		live_values.addRow("PWM", self.pwm_value)
		live_values.addRow("Direction", self.direction_value)
		live_values.addRow("Elapsed time", self.time_value)
		live_values.addRow("Error", self.error_value)
		live_values.addRow("uP", self.proportional_pwm_value)
		live_values.addRow("uI", self.integral_pwm_value)
		live_values.addRow("Requested u", self.requested_pwm_value)
		live_values.addRow("Applied u", self.applied_pwm_value)
		controls_layout.addLayout(live_values, 0, 4, 5, 1)

		# The first plot displays the measured temperature over Arduino time.
		self.temperature_plot = pg.PlotWidget()
		self.temperature_plot.setLabel("bottom", "Time", units="s")
		self.temperature_plot.setLabel("left", "Temperature", units="C")
		self.temperature_plot.enableAutoRange()
		self.temperature_plot.showGrid(x=True, y=True, alpha=0.25)
		self.temperature_plot.addLegend()
		self.temperature_curve = self.temperature_plot.plot(
			pen=pg.mkPen("#d95f02", width=2), name="Temperature"
		)
		self.setpoint_curve = self.temperature_plot.plot(
			pen=pg.mkPen("#008c95", width=2, style=QtCore.Qt.PenStyle.DashLine),
			name="Setpoint",
		)
		# Plot error separately because it is a temperature difference rather than
		# an absolute temperature.
		self.error_plot = pg.PlotWidget()
		self.error_plot.setLabel("bottom", "Time", units="s")
		self.error_plot.setLabel("left", "Error (setpoint - measured)", units="C")
		self.error_plot.showGrid(x=True, y=True, alpha=0.25)
		self.error_curve = self.error_plot.plot(pen=pg.mkPen("#555555", width=2))

		# A signed PWM plot displays magnitude and direction at the same time:
		# positive is HEAT, negative is COOL, and zero is off.
		self.pwm_plot = pg.PlotWidget()
		self.pwm_plot.setLabel("bottom", "Time", units="s")
		self.pwm_plot.setLabel("left", "Signed PWM (+ heat / - cool)")
		self.pwm_plot.setYRange(-255, 255)
		self.pwm_plot.showGrid(x=True, y=True, alpha=0.25)
		self.pwm_plot.addLegend()
		self.pwm_curve = self.pwm_plot.plot(
			pen=pg.mkPen("#000000", width=2), name="Applied u"
		)
		self.proportional_pwm_curve = self.pwm_plot.plot(
			pen=pg.mkPen("#1f78b4", width=2), name="uP"
		)
		self.integral_pwm_curve = self.pwm_plot.plot(
			pen=pg.mkPen("#e66101", width=2), name="uI"
		)
		self.requested_pwm_curve = self.pwm_plot.plot(
			pen=pg.mkPen("#7b3294", width=1, style=QtCore.Qt.PenStyle.DashLine),
			name="Requested u",
		)

		central_widget = QtWidgets.QWidget()
		layout = QtWidgets.QVBoxLayout(central_widget)
		layout.addWidget(controls)
		layout.addWidget(self.temperature_plot)
		layout.addWidget(self.error_plot)
		layout.addWidget(self.pwm_plot)
		self.setCentralWidget(central_widget)

		# Start with the TEC off and put the Arduino under serial control.
		self.serial_port = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
		self.send_control_command(0, "HEAT")
		self.csv_file = open(CSV_FILENAME, "a", newline="")
		self.csv_writer = csv.writer(self.csv_file)
		if self.csv_file.tell() == 0:
			self.csv_writer.writerow(
				[
					"time_s",
					"temperature_C",
					"setpoint_C",
					"error_C",
					"controller_mode",
					"kp_pwm_per_C",
					"ki_pwm_per_C_s",
					"dt_s",
					"integral_error_C_s",
					"u_p_pwm",
					"u_i_pwm",
					"requested_signed_pwm",
					"applied_signed_pwm",
					"arduino_pwm",
					"arduino_heat_cool",
				]
			)
			self.csv_file.flush()

		self.timer = QtCore.QTimer(self)
		self.timer.timeout.connect(self.read_measurements)
		self.timer.start(UPDATE_INTERVAL_MILLISECONDS)

	def set_pwm_value(self, pwm):
		"""Keep the slider and text box synchronized at a valid PWM value."""
		pwm = max(0, min(255, pwm))
		self.pwm_slider.blockSignals(True)
		self.pwm_input.blockSignals(True)
		self.pwm_slider.setValue(pwm)
		self.pwm_input.setText(str(pwm))
		self.pwm_slider.blockSignals(False)
		self.pwm_input.blockSignals(False)
		return pwm

	def send_control_command(self, pwm, direction=None):
		"""Send one direction and PWM command to the Arduino."""
		if direction is None:
			direction = "HEAT" if self.direction_switch.isChecked() else "COOL"
		command = f"SET PWM {pwm} DIR {direction}\n"
		self.serial_port.write(command.encode("ascii"))

	def feedback_enabled(self):
		"""Return True when either feedback controller is selected."""
		return self.control_mode.currentText() in ("P-only", "PI")

	def control_mode_changed(self, mode):
		"""Safely change controller mode and clear integral memory."""
		# Changing modes always passes through zero output so an old command or
		# integral state cannot be applied to the new comparison.
		self.set_pwm_value(0)
		self.send_control_command(0, "HEAT")
		self.zero_integral(update_output=False)
		feedback = mode in ("P-only", "PI")
		self.direction_switch.setEnabled(not feedback)
		self.pwm_slider.setEnabled(not feedback)
		self.pwm_input.setEnabled(not feedback)
		self.integral_gain_input.setEnabled(mode == "PI")
		if feedback:
			self.update_feedback_control(0.0)

	def setpoint_changed(self):
		"""Validate the setpoint and update an active P controller."""
		try:
			setpoint = float(self.setpoint_input.text())
		except ValueError:
			setpoint = INITIAL_SETPOINT_C
		setpoint = max(30.0, min(35.0, setpoint))
		self.setpoint = setpoint
		self.setpoint_input.setText(f"{setpoint:g}")
		if self.feedback_enabled():
			self.update_feedback_control(0.0)

	def gain_changed(self):
		"""Validate the proportional gain and update an active controller."""
		try:
			gain = float(self.gain_input.text())
		except ValueError:
			gain = INITIAL_PROPORTIONAL_GAIN
		gain = max(0.0, min(1000.0, gain))
		self.proportional_gain = gain
		self.gain_input.setText(f"{gain:g}")
		if self.feedback_enabled():
			self.update_feedback_control(0.0)

	def integral_gain_changed(self):
		"""Validate the integral gain without advancing the integral state."""
		try:
			gain = float(self.integral_gain_input.text())
		except ValueError:
			gain = INITIAL_INTEGRAL_GAIN
		gain = max(0.0, min(1000.0, gain))
		self.integral_gain = gain
		self.integral_gain_input.setText(f"{gain:g}")
		if self.feedback_enabled():
			self.update_feedback_control(0.0)

	def zero_integral(self, checked=False, update_output=True):
		"""Clear PI controller memory before a new comparison."""
		self.integral_error = 0.0
		self.integral_output = 0.0
		self.integral_pwm_value.setText("0.00")
		if update_output and self.feedback_enabled():
			self.update_feedback_control(0.0)

	def update_feedback_control(self, delta_time):
		"""Calculate P/PI output and apply conditional-integration anti-windup."""
		if self.latest_temperature is None:
			self.set_pwm_value(0)
			self.send_control_command(0, "HEAT")
			return

		error = self.setpoint - self.latest_temperature
		u_p = self.proportional_gain * error

		if self.control_mode.currentText() == "PI" and delta_time > 0.0:
			candidate_integral = self.integral_error + error * delta_time
			candidate_u_i = self.integral_gain * candidate_integral
			candidate_request = u_p + candidate_u_i
			pushes_high = candidate_request > PWM_LIMIT and error > 0.0
			pushes_low = candidate_request < -PWM_LIMIT and error < 0.0
			if not (pushes_high or pushes_low):
				self.integral_error = candidate_integral

		if self.control_mode.currentText() == "PI":
			u_i = self.integral_gain * self.integral_error
		else:
			self.integral_error = 0.0
			u_i = 0.0

		requested = u_p + u_i
		applied = max(-PWM_LIMIT, min(PWM_LIMIT, requested))
		direction = "HEAT" if applied >= 0.0 else "COOL"
		pwm = int(round(abs(applied)))

		self.proportional_output = u_p
		self.integral_output = u_i
		self.requested_output = requested
		self.applied_output = float(pwm if direction == "HEAT" else -pwm)
		self.error_value.setText(f"{error:.2f} C")
		self.proportional_pwm_value.setText(f"{u_p:.2f}")
		self.integral_pwm_value.setText(f"{u_i:.2f}")
		self.requested_pwm_value.setText(f"{requested:.2f}")
		self.applied_pwm_value.setText(f"{self.applied_output:.0f}")
		self.set_pwm_value(pwm)
		self.direction_switch.setText(direction)
		self.direction_switch.blockSignals(True)
		self.direction_switch.setChecked(direction == "HEAT")
		self.direction_switch.blockSignals(False)
		self.send_control_command(pwm, direction)

	def slider_changed(self, pwm):
		"""Send a command when the user moves the PWM slider."""
		pwm = self.set_pwm_value(pwm)
		self.send_control_command(pwm)

	def text_pwm_changed(self):
		"""Clamp typed PWM input and send the resulting command."""
		try:
			pwm = int(self.pwm_input.text())
		except ValueError:
			pwm = 0
		pwm = self.set_pwm_value(pwm)
		self.send_control_command(pwm)

	def direction_changed(self, heating):
		"""Send the current PWM with the newly selected direction."""
		self.direction_switch.setText("HEAT" if heating else "COOL")
		self.send_control_command(self.pwm_slider.value())

	def read_measurements(self):
		"""Read all currently available lines and process valid ones."""
		if self.serial_port.in_waiting:
			self.serial_buffer += self.serial_port.read(self.serial_port.in_waiting)

		while b"\n" in self.serial_buffer:
			raw_line, self.serial_buffer = self.serial_buffer.split(b"\n", 1)
			line = raw_line.decode("ascii", errors="ignore")
			measurement = parse_measurement(line)
			if measurement is None:
				continue

			time_seconds, temperature, pwm, heat_cool = measurement
			print(
				f"Temperature (C): {temperature:.2f}, "
				f"Time (s): {time_seconds:.2f}, PWM: {pwm}, "
				f"Heat/Cool: {heat_cool}"
			)

			if self.last_measurement_time is None or time_seconds <= self.last_measurement_time:
				delta_time = 0.0
			else:
				delta_time = time_seconds - self.last_measurement_time
			self.last_measurement_time = time_seconds
			self.latest_temperature = temperature

			if self.feedback_enabled():
				self.update_feedback_control(delta_time)
			else:
				self.proportional_output = 0.0
				self.integral_output = 0.0
				self.requested_output = float(pwm if heat_cool else -pwm)
				self.applied_output = self.requested_output
				self.proportional_pwm_value.setText("0.00")
				self.integral_pwm_value.setText("0.00")
				self.requested_pwm_value.setText(f"{self.requested_output:.2f}")
				self.applied_pwm_value.setText(f"{self.applied_output:.0f}")

			error = self.setpoint - temperature
			self.csv_writer.writerow(
				[
					time_seconds,
					temperature,
					self.setpoint,
					error,
					self.control_mode.currentText(),
					self.proportional_gain,
					self.integral_gain,
					delta_time,
					self.integral_error,
					self.proportional_output,
					self.integral_output,
					self.requested_output,
					self.applied_output,
					pwm,
					heat_cool,
				]
			)
			self.csv_file.flush()

			setpoint = self.setpoint
			self.times.append(time_seconds)
			self.temperatures.append(temperature)
			self.setpoints.append(setpoint)
			self.errors.append(error)
			self.signed_pwms.append(self.applied_output)
			self.proportional_pwms.append(self.proportional_output)
			self.integral_pwms.append(self.integral_output)
			self.requested_pwms.append(self.requested_output)

			self.temperature_value.setText(f"{temperature:.2f} C")
			self.pwm_value.setText(str(pwm))
			self.direction_value.setText("HEAT" if heat_cool else "COOL")
			self.time_value.setText(f"{time_seconds:.2f} s")
			self.error_value.setText(f"{error:.2f} C")
			oldest_time = time_seconds - WINDOW_DURATION_SECONDS
			while self.times and self.times[0] < oldest_time:
				self.times.popleft()
				self.temperatures.popleft()
				self.setpoints.popleft()
				self.errors.popleft()
				self.signed_pwms.popleft()
				self.proportional_pwms.popleft()
				self.integral_pwms.popleft()
				self.requested_pwms.popleft()

		# Refresh both plots after processing the available serial data.
		self.temperature_curve.setData(list(self.times), list(self.temperatures))
		self.setpoint_curve.setData(list(self.times), list(self.setpoints))
		self.error_curve.setData(list(self.times), list(self.errors))
		self.pwm_curve.setData(list(self.times), list(self.signed_pwms))
		self.proportional_pwm_curve.setData(
			list(self.times), list(self.proportional_pwms)
		)
		self.integral_pwm_curve.setData(list(self.times), list(self.integral_pwms))
		self.requested_pwm_curve.setData(list(self.times), list(self.requested_pwms))

	def closeEvent(self, event):
		"""Turn the TEC off, then close files and the serial connection."""
		self.timer.stop()
		try:
			self.send_control_command(0, "HEAT")
			self.serial_port.flush()
		except serial.SerialException:
			pass
		self.serial_port.close()
		self.csv_file.close()
		event.accept()


def main():
	"""Start the display application."""
	application = QtWidgets.QApplication(sys.argv)
	window = TemperatureWindow()
	window.resize(900, 500)
	window.show()
	sys.exit(application.exec())


if __name__ == "__main__":
	main()
