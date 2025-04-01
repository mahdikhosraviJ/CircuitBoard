import sys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QMessageBox, QSpinBox, QGridLayout,
    QGroupBox, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator, QIntValidator

# Matplotlib imports for plotting within PyQt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- Matplotlib Canvas Widget ---
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

# --- Main Application Window ---
class MeshAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circuit Board")
        self.setGeometry(100, 100, 800, 700)  # x, y, width, height

        self.resistor_inputs = {}  # Store QLineEdit widgets for resistor values {id: QLineEdit}
        self.mesh_widgets = []  # Store widgets related to each mesh definition
        self.voltage_source_input = None # Store the single voltage source input

        self._create_widgets()
        self._create_layout()

    def _create_widgets(self):
        # Input Sections
        self.num_resistors_spinbox = QSpinBox()
        self.num_resistors_spinbox.setMinimum(1)
        self.num_resistors_spinbox.valueChanged.connect(self._update_resistor_inputs)  # Connect signal

        self.voltage_source_input = QLineEdit()
        self.voltage_source_input.setValidator(QDoubleValidator())  # Allow floats
        self.voltage_source_input.setPlaceholderText("e.g., 9.0")

        self.num_meshes_spinbox = QSpinBox()
        self.num_meshes_spinbox.setMinimum(1)
        self.num_meshes_spinbox.valueChanged.connect(self._update_mesh_inputs)  # Connect signal

        # Placeholders for dynamic inputs
        self.resistors_groupbox = QGroupBox("Resistor Values (Ohms)")
        self.resistors_layout = QVBoxLayout()  # Or QFormLayout
        self.resistors_groupbox.setLayout(self.resistors_layout)

        self.mesh_definitions_groupbox = QGroupBox("Mesh Definitions")
        self.mesh_definitions_layout = QVBoxLayout()
        self.mesh_definitions_groupbox.setLayout(self.mesh_definitions_layout)

        self.shared_resistors_input = QTextEdit()
        self.shared_resistors_input.setPlaceholderText(
            "Enter shared resistors, one per line:\nR_ID, Mesh_ID1, Mesh_ID2\n(e.g., 3, 1, 2)")
        self.shared_resistors_input.setFixedHeight(100)  # Limit height

        # Calculation Button
        self.calculate_button = QPushButton("Calculate Mesh Currents")
        self.calculate_button.clicked.connect(self.perform_mesh_analysis)

        # Output Section
        self.results_output = QTextEdit()
        self.results_output.setReadOnly(True)
        self.results_output.setPlaceholderText("Results (Matrices R, V, and Mesh Currents I) will appear here.")

        # Plotting Section
        self.plot_canvas = MplCanvas(self, width=5, height=3, dpi=100)

    def _create_layout(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)  # Main horizontal split

        # --- Left Side: Inputs ---
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)

        # Basic Params
        params_groupbox = QGroupBox("Basic Parameters")
        params_layout = QGridLayout()
        params_layout.addWidget(QLabel("Number of Resistors:"), 0, 0)
        params_layout.addWidget(self.num_resistors_spinbox, 0, 1)
        params_layout.addWidget(QLabel("Main Voltage Source (V):"), 1, 0)
        params_layout.addWidget(self.voltage_source_input, 1, 1)
        params_layout.addWidget(QLabel("Number of Meshes:"), 2, 0)
        params_layout.addWidget(self.num_meshes_spinbox, 2, 1)
        params_groupbox.setLayout(params_layout)

        input_layout.addWidget(params_groupbox)

        # Scroll Area for potentially many resistors/meshes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        scroll_layout.addWidget(self.resistors_groupbox)
        scroll_layout.addWidget(self.mesh_definitions_groupbox)
        shared_groupbox = QGroupBox("Shared Resistors")
        shared_layout = QVBoxLayout()
        shared_layout.addWidget(self.shared_resistors_input)
        shared_groupbox.setLayout(shared_layout)
        scroll_layout.addWidget(shared_groupbox)
        scroll_area.setWidget(scroll_widget)

        input_layout.addWidget(scroll_area)  # Add scroll area to main input layout
        input_layout.addWidget(self.calculate_button)
        input_layout.addStretch(1)  # Push button up if space allows

        # --- Right Side: Outputs ---
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.addWidget(QLabel("Calculation Results:"))
        output_layout.addWidget(self.results_output, stretch=1)  # Give text edit more space
        output_layout.addWidget(QLabel("Mesh Currents Plot:"))
        output_layout.addWidget(self.plot_canvas, stretch=1)  # Give plot space

        # Add input and output sides to main layout
        main_layout.addWidget(input_widget, stretch=1)  # Give input side some stretch factor
        main_layout.addWidget(output_widget, stretch=2)  # Give output side more space

        self.setCentralWidget(main_widget)
        self._update_resistor_inputs()  # Initial setup
        self._update_mesh_inputs()    # Initial setup

    def _update_resistor_inputs(self):
        num_resistors = self.num_resistors_spinbox.value()
        # Clear existing widgets from layout first
        while self.resistors_layout.count():
            item = self.resistors_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.resistor_inputs.clear()

        # Add new input fields
        res_form_layout = QGridLayout()  # Use grid for better alignment
        for i in range(num_resistors):
            res_id = i + 1
            label = QLabel(f"R{res_id} (Ohm):")
            line_edit = QLineEdit()
            line_edit.setValidator(QDoubleValidator(0.001, 1.0e9, 3))  # Min > 0, Max large, 3 decimals
            line_edit.setPlaceholderText("e.g., 100.0")
            self.resistor_inputs[res_id] = line_edit
            res_form_layout.addWidget(label, i, 0)
            res_form_layout.addWidget(line_edit, i, 1)
        self.resistors_layout.addLayout(res_form_layout)

    def _update_mesh_inputs(self):
        num_meshes = self.num_meshes_spinbox.value()
        # Clear existing widgets
        while self.mesh_definitions_layout.count():
            item = self.mesh_definitions_layout.takeAt(0)
            layout_item = item.layout()
            widget_item = item.widget()
            if layout_item is not None:
                # Recursively clear layout items
                while layout_item.count():
                    sub_item = layout_item.takeAt(0)
                    sub_widget = sub_item.widget()
                    if sub_widget:
                        sub_widget.deleteLater()
                # Delete layout itself? Usually not needed if parent widget is deleted
            if widget_item is not None:
                widget_item.deleteLater()
        self.mesh_widgets.clear()

        # Add new input fields for each mesh
        for i in range(num_meshes):
            mesh_id = i + 1
            mesh_groupbox = QGroupBox(f"Mesh {mesh_id}")
            mesh_layout = QVBoxLayout()

            res_ids_label = QLabel(f"Resistor IDs in Mesh {mesh_id} (comma-separated):")
            res_ids_input = QLineEdit()
            res_ids_input.setPlaceholderText("e.g., 1, 3, 4")

            mesh_layout.addWidget(res_ids_label)
            mesh_layout.addWidget(res_ids_input)
            mesh_groupbox.setLayout(mesh_layout)

            self.mesh_definitions_layout.addWidget(mesh_groupbox)
            # Store references to the input widgets for later retrieval
            self.mesh_widgets.append({
                'groupbox': mesh_groupbox,
                'res_ids_input': res_ids_input,
                'v_mesh_input': None # No voltage input per mesh anymore
            })

    def perform_mesh_analysis(self):
        self.results_output.clear()  # Clear previous results
        try:
            # --- 1. Read Input Values ---
            num_resistors = self.num_resistors_spinbox.value()
            num_meshes = self.num_meshes_spinbox.value()
            voltage_source_value = self.voltage_source_input.text().strip()

            if not voltage_source_value:
                raise ValueError("Missing value for the main voltage source.")
            voltage_source = float(voltage_source_value)

            # Read resistor values
            resistor_values = {}
            for res_id, line_edit in self.resistor_inputs.items():
                value_str = line_edit.text().strip()
                if not value_str:
                    raise ValueError(f"Missing value for Resistor R{res_id}")
                value = float(value_str)
                if value <= 0:
                    raise ValueError(f"Resistance R{res_id} must be positive")
                resistor_values[res_id] = value

            if len(resistor_values) != num_resistors:
                # This check might be redundant if _update_resistor_inputs works correctly
                raise ValueError("Mismatch between expected and entered number of resistors.")

            # Initialize Matrices
            R_matrix = np.zeros((num_meshes, num_meshes))
            V_vector = np.zeros(num_meshes)
            mesh_definitions = {}  # Store {mesh_id: set(res_ids)}

            # Read Mesh Definitions (Diagonal R and V vector)
            for i in range(num_meshes):
                mesh_id = i + 1
                widgets = self.mesh_widgets[i]
                res_ids_input = widgets['res_ids_input']

                res_ids_str = res_ids_input.text().strip()
                if not res_ids_str:
                    raise ValueError(f"Missing resistor IDs for Mesh {mesh_id}")
                res_ids = [int(r_id.strip()) for r_id in res_ids_str.split(',')]

                total_r_in_mesh = 0
                valid_ids = True
                current_mesh_resistors = set()
                for r_id in res_ids:
                    if r_id not in resistor_values:
                        raise ValueError(
                            f"Resistor R{r_id} (in Mesh {mesh_id}) was not defined or has no value")
                    total_r_in_mesh += resistor_values[r_id]
                    current_mesh_resistors.add(r_id)

                R_matrix[i, i] = total_r_in_mesh
                mesh_definitions[mesh_id] = current_mesh_resistors
                V_vector[i] = voltage_source # Assumes the same voltage source for all meshes.


            # Read Shared Resistors (Off-diagonal R)
            shared_lines = self.shared_resistors_input.toPlainText().strip().split('\n')
            for line in shared_lines:
                line = line.strip()
                if not line:
                    continue  # Skip empty lines

                parts_str = line.split(',')
                if len(parts_str) != 3:
                    raise ValueError(
                        f"Invalid format for shared resistor: '{line}'. Use R_ID, Mesh_ID1, Mesh_ID2")
                parts = [int(p.strip()) for p in parts_str]
                r_id, mesh1_id, mesh2_id = parts

                if r_id not in resistor_values:
                    raise ValueError(f"Shared resistor R{r_id} not defined.")
                if not (1 <= mesh1_id <= num_meshes and 1 <= mesh2_id <= num_meshes):
                    raise ValueError(f"Invalid Mesh ID in shared definition: '{line}'")
                if mesh1_id == mesh2_id:
                    raise ValueError(
                        f"Shared resistor must be between two different meshes: '{line}'")

                r_shared_value = resistor_values[r_id]
                idx1 = mesh1_id - 1
                idx2 = mesh2_id - 1
                R_matrix[idx1, idx2] -= r_shared_value
                R_matrix[idx2, idx1] -= r_shared_value

            # --- 2. Solve the System ---
            self.results_output.append("--- Input Summary ---")
            self.results_output.append(f"Main Voltage Source: {voltage_source} V")
            self.results_output.append(f"Resistors: {resistor_values}")
            self.results_output.append(f"Mesh Definitions: {mesh_definitions}")
            self.results_output.append(f"Shared Input Lines: {shared_lines}\n")

            self.results_output.append("--- Calculation ---")
            self.results_output.append("Resistance Matrix [R]:")
            self.results_output.append(str(R_matrix))
            self.results_output.append("\nVoltage Vector [V]:")
            self.results_output.append(str(V_vector))

            try:
                mesh_currents = np.linalg.solve(R_matrix, V_vector)
            except np.linalg.LinAlgError:
                raise np.linalg.LinAlgError("The resistance matrix is singular. Cannot solve the system.\nPlease check mesh definitions and shared resistors.")

            self.results_output.append("\n--- Results ---")
            self.results_output.append("Mesh Currents [I]:")
            current_results = {}
            for i, current in enumerate(mesh_currents):
                self.results_output.append(f"  Mesh {i + 1} Current (I{i + 1}): {current:.4f} Amperes")
                current_results[f"I{i + 1}"] = current

            # --- 3. Update Plot ---
            self.update_plot(current_results)

        except ValueError as ve:
            QMessageBox.warning(self, "Input Error", f"Invalid input: {ve}")
            self.results_output.append(f"\nError: Invalid input - {ve}")
            self.clear_plot()
        except np.linalg.LinAlgError as lae:
            QMessageBox.critical(self, "Calculation Error", str(lae))
            self.results_output.append(f"\nError: {lae}")
            self.clear_plot()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
            self.results_output.append(f"\nError: {e}")
            self.clear_plot()

    def update_plot(self, current_results):
        """Updates the matplotlib canvas with a bar chart of mesh currents."""
        if not current_results:
            self.clear_plot()
            return

        labels = list(current_results.keys())
        values = list(current_results.values())

        ax = self.plot_canvas.axes
        ax.cla()  # Clear previous plot
        ax.bar(labels, values)
        ax.set_ylabel("Current (Amperes)")
        ax.set_xlabel("Mesh")
        ax.set_title("Calculated Mesh Currents")
        ax.tick_params(axis='x', rotation=45)  # Rotate labels if many meshes
        self.plot_canvas.fig.tight_layout()  # Adjust layout
        self.plot_canvas.draw()

    def clear_plot(self):
        """Clears the plot area."""
        ax = self.plot_canvas.axes
        ax.cla()
        ax.set_title("Mesh Currents Plot")
        ax.set_xlabel("")
        ax.set_ylabel("")
        self.plot_canvas.draw()



# --- Run the Application ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MeshAnalysisApp()
    window.show()
    sys.exit(app.exec())
