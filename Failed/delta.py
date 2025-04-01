import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QGridLayout, QTextEdit,
    QDialog, QFormLayout, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt
import sympy as sp
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt6 import QtGui
from matplotlib.path import Path
import matplotlib.patches as patches
import math

class BatteryDialog(QDialog):
    def __init__(self, nodes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Battery Details")
        self.node1_combo = QComboBox()
        self.node2_combo = QComboBox()
        self.voltage_edit = QLineEdit()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.nodes = nodes

        self.node1_combo.addItems(nodes)
        self.node2_combo.addItems(nodes)
        self.voltage_edit.setValidator(QtGui.QDoubleValidator())  #restricts input

        layout = QFormLayout()
        layout.addRow("Positive Terminal Node:", self.node1_combo)
        layout.addRow("Negative Terminal Node:", self.node2_combo)
        layout.addRow("Voltage (V):", self.voltage_edit)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)



    def get_data(self):
        return {
            "node1": self.node1_combo.currentText(),
            "node2": self.node2_combo.currentText(),
            "voltage": float(self.voltage_edit.text()),
        }


class ResistorDialog(QDialog):
    def __init__(self, nodes, index, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Resistor {index + 1} Data")
        self.node1_combo = QComboBox()
        self.node2_combo = QComboBox()
        self.resistance_edit = QLineEdit()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.nodes = nodes

        self.node1_combo.addItems(nodes)
        self.node2_combo.addItems(nodes)
        self.resistance_edit.setValidator(QtGui.QDoubleValidator()) #restricts input

        layout = QFormLayout()
        layout.addRow("Node 1:", self.node1_combo)
        layout.addRow("Node 2:", self.node2_combo)
        layout.addRow("Resistance (Ω):", self.resistance_edit)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)



    def get_data(self):
        return {
            "node1": self.node1_combo.currentText(),
            "node2": self.node2_combo.currentText(),
            "resistance": float(self.resistance_edit.text()),
        }



class NodeAnalysisWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.graph = nx.Graph()
        self.nodes = {}
        self.components = {}
        self.voltage_source_present = False
        self.figure = None
        self.canvas = None
        self.resistor_data = []
        self.battery_dialog = None #added
        self.ground_node = None
        self.layout_method = 'spring'  # Default layout method
        self.num_resistors = 0
        self.solutions = {}
        self.current_calculation_method = 'branch' # or 'total'

    def initUI(self):
        self.setWindowTitle("Circuit Analysis")
        self.setGeometry(100, 100, 800, 600)

        self.num_nodes_label = QLabel("Number of Nodes:")
        self.num_nodes_edit = QLineEdit()
        self.num_resistors_label = QLabel("Number of Resistors:")
        self.num_resistors_edit = QLineEdit()
        self.ground_node_label = QLabel("Ground Node:")
        self.ground_node_combo = QComboBox()
        self.layout_label = QLabel("Layout Method:")
        self.layout_combo = QComboBox()  # Add the layout combo box
        self.layout_combo.addItems(['circular', 'planar'])  # Add layout options
        self.current_calculation_label = QLabel("Current Calculation:")
        self.current_calculation_combo = QComboBox()
        self.current_calculation_combo.addItems(['branch', 'total'])
        self.enter_data_button = QPushButton("Enter Circuit Data")
        self.solve_button = QPushButton("Solve")
        self.solve_button.setEnabled(False)
        self.plot_button = QPushButton("Show Circuit Map")
        self.plot_button.setEnabled(False)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)

        self.figure = plt.figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)

        grid_layout = QGridLayout()
        grid_layout.addWidget(self.num_nodes_label, 0, 0)
        grid_layout.addWidget(self.num_nodes_edit, 0, 1)
        grid_layout.addWidget(self.num_resistors_label, 1, 0)
        grid_layout.addWidget(self.num_resistors_edit, 1, 1)
        grid_layout.addWidget(self.ground_node_label, 2, 0)
        grid_layout.addWidget(self.ground_node_combo, 2, 1)
        grid_layout.addWidget(self.layout_label, 3, 0)  # Add layout label
        grid_layout.addWidget(self.layout_combo, 3, 1)  # Add layout combo box
        grid_layout.addWidget(self.current_calculation_label, 4, 0)
        grid_layout.addWidget(self.current_calculation_combo, 4, 1)
        grid_layout.addWidget(self.enter_data_button, 5, 0, 1, 2)
        grid_layout.addWidget(self.solve_button, 6, 0, 1, 2)
        grid_layout.addWidget(self.plot_button, 7, 0, 1, 2)
        grid_layout.addWidget(self.output_text, 8, 0, 2, 5)
        grid_layout.addWidget(self.canvas, 0, 2, 7, 3)

        self.setLayout(grid_layout)

        self.num_nodes_edit.setValidator(QtGui.QIntValidator())  # Only integers allowed
        self.num_resistors_edit.setValidator(QtGui.QIntValidator())
        self.enter_data_button.clicked.connect(self.enter_data)
        self.solve_button.clicked.connect(self.solve_analysis)
        self.plot_button.clicked.connect(self.plot_circuit)
        self.layout_combo.currentIndexChanged.connect(self.on_layout_changed) # Connect the layout combo box
        self.current_calculation_combo.currentIndexChanged.connect(self.on_current_calculation_changed)

    def on_current_calculation_changed(self):
        self.current_calculation_method = self.current_calculation_combo.currentText()

    def on_layout_changed(self):
        """
        Called when the user selects a different layout method from the combo box.
        """
        self.layout_method = self.layout_combo.currentText()

    def enter_data(self):
        try:
            num_nodes = int(self.num_nodes_edit.text())
            self.num_resistors = int(self.num_resistors_edit.text())  # Get number of resistors
            if num_nodes < 2:
                QMessageBox.warning(self, "Input Error", "Number of nodes must be at least 2.")
                return
            if self.num_resistors < 1:
                QMessageBox.warning(self, "Input Error", "Number of resistors must be at least 1.")
                return
            if self.num_resistors != num_nodes - 1:
                QMessageBox.warning(self, "Input Error", "For this circuit, the number of resistors must be one less than the number of nodes.")
                return

            # Generate node names automatically (A, B, C, ...)
            self.nodes = {chr(ord('A') + i): chr(ord('A') + i) for i in range(num_nodes)}
            node_names = list(self.nodes.keys())
            self.ground_node_combo.clear()
            self.ground_node_combo.addItems(node_names)


            # Get Battery Data
            self.battery_dialog = BatteryDialog(node_names, self) #initialize
            if self.battery_dialog.exec() == QDialog.DialogCode.Accepted:
                battery_data = self.battery_dialog.get_data()
                vs_node1 = battery_data["node1"]
                vs_node2 = battery_data["node2"]
                vs_value = battery_data["voltage"]
                if vs_node1 == vs_node2:
                    QMessageBox.warning(self, "Input Error", "Battery terminals cannot be connected to the same node")
                    return
                if vs_value <= 0:
                    QMessageBox.warning(self, "Input Error", "Battery voltage must be greater than 0")
                    return

                self.voltage_source_present = True
                self.voltage_source_data = {"node1": vs_node1, "node2": vs_node2, "value": vs_value}
            else:
                return  # User cancelled

            # num_resistors = num_nodes - 1 #removed
            self.resistor_data = []
            for i in range(self.num_resistors):
                resistor_dialog = ResistorDialog(node_names, i, self)
                if resistor_dialog.exec() == QDialog.DialogCode.Accepted:
                    resistor_data = resistor_dialog.get_data()
                    if resistor_data["node1"] == resistor_data["node2"]:
                        QMessageBox.warning(self, f"Input Error", f"Resistor {i+1} terminals cannot be connected to the same node")
                        return
                    if resistor_data["resistance"] <= 0:
                         QMessageBox.warning(self, f"Input Error", f"Resistor {i+1} resistance must be greater than 0")
                         return
                    self.resistor_data.append(resistor_data)
                else:
                    return

            self.graph = nx.Graph()
            self.graph.add_nodes_from(node_names)



            # Add voltage source
            self.graph.add_edge(vs_node1, vs_node2, type="Voltage Source", value=vs_value, name="Vs")
            self.components["Vs"] = {"type": "Voltage Source", "node1": vs_node1, "node2": vs_node2, "value": vs_value}

            # Add resistors
            node_list = list(self.nodes.keys())
            for i, resistor_data in enumerate(self.resistor_data):
                node1 = node_list[i]
                node2 = node_list[i+1]
                resistance = resistor_data["resistance"]
                resistor_name = f"R{i + 1}"
                self.graph.add_edge(node1, node2, type="Resistor", value=resistance, name=resistor_name)
                self.components[resistor_name] = {"type": "Resistor", "node1": node1, "node2": node2, "value": resistance}
            #make sure the circuit is closed for 3 nodes.
            if num_nodes == 3:
                self.graph.add_edge(node_names[0],node_names[2], type="Resistor", value=1, name="R3") #default resistance
                self.components["R3"] = {"type": "Resistor", "node1": node_names[0], "node2": node_names[2], "value": 1}

            self.solve_button.setEnabled(True)
            self.plot_button.setEnabled(True)
            self.output_text.append("Data Entered.")
            # self.ground_node = self.ground_node_combo.currentText() #removed
            self.ground_node = self.choose_ground_node()

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numbers.")
            return
        except IndexError:
            QMessageBox.warning(self, "Input Error", "Incorrect number of nodes or components provided.")
            return

    def choose_ground_node(self):
        """
        Chooses the ground node based on node connectivity.  Selects the
        node with the highest degree (most connections).
        """
        degrees = dict(self.graph.degree())
        most_connected_node = max(degrees, key=degrees.get)
        return most_connected_node

    def solve_analysis(self):
        result_text = "Solving circuit analysis using NetworkX and SymPy...\n"
        result_text += f"Nodes: {self.graph.nodes}\n"
        result_text += f"Edges: {self.graph.edges(data=True)}\n"
        equations = self.generate_node_equations()

        if equations:
            result_text += "\nNode Equations:\n"
            for eq in equations:
                result_text += f"{eq}\n"
            # Solve the equations using sympy
            symbols = [sp.Symbol(f"V_{node}") for node in self.nodes if node != self.ground_node]
            try:
                self.solutions = sp.solve(equations, symbols) # Store the solutions
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error solving equations: {e}")
                return

            if self.solutions:
                result_text += "\nNode Voltages:\n"
                for node, voltage in self.solutions.items():
                    result_text += f"{node} = {voltage} V\n"
                result_text += f"{self.ground_node} = 0 V\n" #add ground node

                # Calculate branch currents
                result_text += "\nBranch Currents:\n"
                for edge in self.graph.edges(data=True):
                    node1, node2, data = edge
                    v1 = self.solutions.get(sp.Symbol(f"V_{node1}"))
                    v2 = self.solutions.get(sp.Symbol(f"V_{node2}"))
                    if v1 is None:
                        v1 = 0
                    if v2 is None:
                        v2 = 0
                    current = (v1 - v2) / data["value"]
                    result_text += f"Current through {node1}-{node2} ({data['name']}): {current} A\n"
                if self.current_calculation_method == 'total':
                    result_text += self.calculate_total_current()
        else:
            result_text += "\nNo independent node equations generated.\n"

        self.output_text.setPlainText(result_text)

    def calculate_total_current(self):
        """Calculates the total current flowing through the circuit.
        Returns:
            float: The total current in Amperes, or None if it cannot be calculated.
        """
        total_current = 0
        voltage_sources = [comp for comp_name, comp in self.components.items() if comp['type'] == 'Voltage Source']
        if not voltage_sources:
            return "\nTotal Current: Cannot calculate, no voltage source found.\n"

        # For simplicity, assume one voltage source.  If you have multiple, you'll need to decide how they combine.
        vs_node1 = voltage_sources[0]['node1']
        vs_node2 = voltage_sources[0]['node2']
        vs_value = voltage_sources[0]['value']

        v1 = self.solutions.get(sp.Symbol(f"V_{vs_node1}"))
        v2 = self.solutions.get(sp.Symbol(f"V_{vs_node2}"))
        if v1 is None:
            v1 = 0
        if v2 is None:
            v2 = 0
        try:
            total_current = (v1 - v2) / vs_value #error
        except ZeroDivisionError:
            return "\nTotal Current: Cannot calculate, voltage source value is zero.\n"
        return f"\nTotal Current: {total_current} A\n"

    def generate_node_equations(self):
        node_voltages = {node: sp.symbols(f"V_{node}") for node in self.nodes if node != self.ground_node}
        equations = []

        for node_name in self.nodes:
            if node_name != self.ground_node:
                equation = 0
                for neighbor in self.graph.neighbors(node_name):
                    edge_data = self.graph.get_edge_data(node_name, neighbor)
                    if edge_data["type"] == "Resistor":
                        equation += (node_voltages[node_name] - (0 if neighbor == self.ground_node else node_voltages[neighbor])) / edge_data["value"]
                    elif edge_data["type"] == "Voltage Source":
                        if neighbor == self.ground_node:
                            equation += (node_voltages[node_name] - 0) / sp.oo
                        else:
                            equation += (node_voltages[node_name] - node_voltages[neighbor]) / sp.oo
                equations.append(equation)
        return equations

    def plot_circuit(self):
        """
        Plots the  circuit.
        """
        if self.figure is None:
            self.figure = plt.figure(figsize=(8, 6))
            self.canvas = FigureCanvas(self.figure)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        #pos = nx.spring_layout(self.graph)
        # if self.layout_method == 'spring':
        #     pos = nx.spring_layout(self.graph)
        if self.layout_method == 'circular':
            pos = nx.circular_layout(self.graph)
        elif self.layout_method == 'planar':
            pos = nx.planar_layout(self.graph)
        else:
            pos =  nx.circular_layout(self.graph) #default

        # Custom node labels
        node_labels = {node: node for node in self.graph.nodes()}
        nx.draw_networkx_nodes(self.graph, pos, node_color='lightblue', node_size=500, ax=ax)
        nx.draw_networkx_labels(self.graph, pos, labels=node_labels, font_size=10, ax=ax)

        # Add edge labels and styles
        edge_labels = {}
        edge_style = {}
        for u, v, data in self.graph.edges(data=True):
            label = data['name']
            if data['type'] == 'Resistor':
                edge_style[(u, v)] = 'solid'
                label = f"R: {label}"
            elif data['type'] == 'Voltage Source':
                edge_style[(u, v)] = 'dashed'
                label = "Battery"
            edge_labels[(u, v)] = label

        # Convert edge_style to a list of styles, one for each edge in the order that they are drawn.
        edge_styles = [edge_style[(u, v)] for u, v in self.graph.edges()]
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels, font_size=10, ax=ax)
        nx.draw_networkx_edges(self.graph, pos, style=edge_styles, ax=ax) # Pass the list of styles.

        ax.set_title(f"Circuit Map ({self.layout_method.capitalize()} Layout)")
        self.canvas.draw()
        self.output_text.append("Circuit Map Plotted.")
        self.canvas.show()

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QStyleFactory
    app = QApplication(sys.argv)
    #app.setStyle(QStyleFactory.create('Fusion')) #sets the style
    window = NodeAnalysisWindow()
    window.show()
    sys.exit(app.exec())
