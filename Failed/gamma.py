import sys
import numpy as np
import networkx as nx
from typing import List, Dict, Optional, Tuple, Set, Any # Added for type hinting

# Removed matplotlib import as it wasn't used for plotting within the Qt app directly
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # Incorrect backend
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
                             QScrollArea, QGridLayout, QGraphicsScene, QGraphicsView,
                             QGraphicsRectItem, QGraphicsTextItem, QInputDialog,
                             QGraphicsEllipseItem, QGraphicsLineItem, QMessageBox, QGraphicsItem,
                             QGraphicsPathItem, QSizePolicy, QStyleOptionGraphicsItem, # Added QStyleOptionGraphicsItem
                             QGraphicsSceneMouseEvent, QStyle, QMainWindow, QMenu, # Added QStyle, QMainWindow, QMenu
                             QMenuBar) # Added QMenuBar
from PyQt6.QtCore import Qt, QPointF, QRectF, QLineF, QSizeF, QSize # Added QSize
from PyQt6.QtGui import (QColor, QFont, QPen, QCursor, QTransform, QPainterPath, QBrush, QPainter, # QPainterPath is needed
                         QWheelEvent, QMouseEvent, QKeyEvent, QAction, QIcon, QKeySequence) # Added QAction, QIcon, QKeySequence

# --- Constants ---
GRID_SIZE: int = 32 # Smaller grid size for finer placement
DOT_SIZE: int = 8
ICON_SIZE: QSize = QSize(16, 16) # Standard size for menu/button icons

# --- Helper Function ---
def get_other_dot(component: 'CircuitComponent', dot: QGraphicsEllipseItem) -> Optional[QGraphicsEllipseItem]:
    """Returns the other connection dot of a component."""
    if not component or not dot: return None # Basic check
    if dot is component.dot1:
        return component.dot2
    elif dot is component.dot2:
        return component.dot1
    return None

class ConnectionLine(QGraphicsPathItem): # Inherit from QGraphicsPathItem
    """Represents an orthogonal connection wire between two component dots."""
    def __init__(self, dot1: QGraphicsEllipseItem, dot2: QGraphicsEllipseItem, parent: Optional[QGraphicsItem]=None):
        super().__init__(parent)
        self.dot1: QGraphicsEllipseItem = dot1 # Starting QGraphicsEllipseItem
        self.dot2: QGraphicsEllipseItem = dot2 # Ending QGraphicsEllipseItem
        self.setPen(QPen(QColor(0, 0, 200), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.setZValue(0) # Ensure lines are behind components
        self.update_path() # Use update_path instead of update_position

    def get_component1(self) -> Optional['CircuitComponent']:
        # Added forward reference for CircuitComponent type hint
        if not self.dot1: return None
        parent = self.dot1.parentItem()
        return parent if isinstance(parent, CircuitComponent) else None

    def get_component2(self) -> Optional['CircuitComponent']:
        # Added forward reference for CircuitComponent type hint
        if not self.dot2: return None
        parent = self.dot2.parentItem()
        return parent if isinstance(parent, CircuitComponent) else None

    def update_path(self) -> None:
        """Updates the orthogonal path between the centers of the connected dots.
           Chooses between HV (Horizontal-Vertical) and VH (Vertical-Horizontal) routing.
        """
        if not self.dot1 or not self.dot2 or not self.dot1.scene() or not self.dot2.scene():
            self.setPath(QPainterPath()) # Clear path if dots are invalid or not in scene
            return

        # Calculate center points of the dots in scene coordinates
        try:
            p1: QPointF = self.dot1.scenePos() + QPointF(DOT_SIZE / 2, DOT_SIZE / 2)
            p2: QPointF = self.dot2.scenePos() + QPointF(DOT_SIZE / 2, DOT_SIZE / 2)
        except RuntimeError: # Catch if item is being destroyed
             self.setPath(QPainterPath())
             return


        path = QPainterPath()
        path.moveTo(p1)

        dx: float = p2.x() - p1.x()
        dy: float = p2.y() - p1.y()

        # Check if points are significantly different to need orthogonal routing
        if abs(dx) > 0.1 and abs(dy) > 0.1:
            # Choose routing based on the longer distance (prioritize longer straight segment)
            if abs(dx) >= abs(dy):
                # Horizontal first is longer or equal: Use HV routing
                intermediate_point = QPointF(p2.x(), p1.y())
                path.lineTo(intermediate_point)
            else:
                # Vertical first is longer: Use VH routing
                intermediate_point = QPointF(p1.x(), p2.y())
                path.lineTo(intermediate_point)

            path.lineTo(p2) # Final segment to the destination
        else:
             # If already aligned horizontally or vertically, just draw a straight line
             path.lineTo(p2)

        self.setPath(path)

    # Override shape() and boundingRect() for better interaction if needed,
    # but default implementation might be sufficient for lines.
    # def shape(self) -> QPainterPath: # For accurate collision detection
    #     # Create a shape that follows the path with some thickness
    #     stroker = QPainterPathStroker()
    #     stroker.setWidth(5) # Make the clickable area slightly wider than the pen
    #     return stroker.createStroke(self.path())

    # def boundingRect(self) -> QRectF: # Ensure the bounding rect covers the path
    #     # Add some padding to the path's bounding rect
    #     return self.path().boundingRect().adjusted(-2, -2, 2, 2)


    def __eq__(self, other: Any) -> bool:
        """Check equality based on connected dots (order doesn't matter)."""
        if not isinstance(other, ConnectionLine):
            return NotImplemented
        # Check if the dots being connected are the same pair
        # Ensure dots exist before comparing
        if not self.dot1 or not self.dot2 or not other.dot1 or not other.dot2:
             return False # Cannot compare if dots are missing
        return ( (self.dot1 == other.dot1 and self.dot2 == other.dot2) or \
                 (self.dot1 == other.dot2 and self.dot2 == other.dot1) )

    def __hash__(self) -> int:
        """Hashing based on connected dots (order doesn't matter)."""
        # Use frozenset of the dots themselves for hashing
        # Ensure dots are not None before hashing
        dots_set = frozenset([d for d in [self.dot1, self.dot2] if d is not None])
        return hash(dots_set)


class CircuitComponent(QGraphicsItem):
    """Represents a circuit component (Resistor or Voltage Source) in the scene."""
    def __init__(self, name: str, value: float, component_type: str, x: float, y: float):
        super().__init__()
        self.name: str = name
        self.value: float = float(value) # Ensure value is float for calculations
        self.component_type: str = component_type
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges) # Notify on movement

        self.lines: Set[ConnectionLine] = set() # Use a set to store associated ConnectionLine objects
        self.dots: List[QGraphicsEllipseItem] = []
        self.snap_to_grid: bool = True
        self.z_value: int = 10 # Ensure components are above lines and grid
        self.setZValue(self.z_value)
        self.highlighted: bool = False

        self.width: int = 0
        self.height: int = 0
        self.text_str: str = ""
        self.color: QColor = QColor("lightgrey")
        self.shape_type: str = "rect" # Default

        # Define the shape and text based on component type
        if component_type == "R":
            self.width = 60
            self.height = 30
            self.text_str = f"{name}\n{value} Ω"
            self.color = QColor(240, 200, 200) # Light Coral
            self.shape_type = "rect"
        elif component_type == "V":
            self.width = 40
            self.height = 40
            # Indicate polarity (+ at top/left, - at bottom/right)
            self.text_str = f"{name}\n{value} V\n(+/-)"
            self.color = QColor(200, 240, 200) # Light Green
            self.shape_type = "ellipse"
        else: # Default/Unknown
            self.width = 50
            self.height = 50
            self.text_str = f"U:{name}\n{value}"
            self.color = QColor("lightgrey")
            self.shape_type = "rect"

        self.text: QGraphicsTextItem = QGraphicsTextItem(self.text_str, self)
        self.text.setFont(QFont("Arial", 8)) # Smaller font
        self.text.setDefaultTextColor(QColor(30, 30, 30))
        # Center text - adjust position based on shape
        text_rect: QRectF = self.text.boundingRect()
        if self.shape_type == "rect":
            self.text.setPos((self.width - text_rect.width()) / 2, (self.height - text_rect.height()) / 2)
        else: # Ellipse
             self.text.setPos((self.width - text_rect.width()) / 2, (self.height - text_rect.height()) / 2)


        # Add connection dots. Store references.
        dot_brush: QBrush = QBrush(QColor("red"))
        dot_pen: QPen = QPen(QColor(100, 0, 0))
        self.dot1: Optional[QGraphicsEllipseItem] = None # Initialize
        self.dot2: Optional[QGraphicsEllipseItem] = None # Initialize

        if self.shape_type == "rect": # Resistor or Unknown
            # Left dot
            self.dot1 = QGraphicsEllipseItem(-DOT_SIZE / 2, self.height / 2 - DOT_SIZE / 2, DOT_SIZE, DOT_SIZE, self)
            # Right dot
            self.dot2 = QGraphicsEllipseItem(self.width - DOT_SIZE / 2, self.height / 2 - DOT_SIZE / 2, DOT_SIZE, DOT_SIZE, self)
        else: # Ellipse (Voltage Source) - Top/Bottom
            # Top dot (+)
            self.dot1 = QGraphicsEllipseItem(self.width / 2 - DOT_SIZE / 2, -DOT_SIZE / 2, DOT_SIZE, DOT_SIZE, self)
             # Bottom dot (-)
            self.dot2 = QGraphicsEllipseItem(self.width / 2 - DOT_SIZE / 2, self.height - DOT_SIZE / 2, DOT_SIZE, DOT_SIZE, self)

        # Add valid dots to the list
        if self.dot1: self.dots.append(self.dot1)
        if self.dot2: self.dots.append(self.dot2)

        for dot in self.dots:
            dot.setBrush(dot_brush)
            dot.setPen(dot_pen)
            # Don't make dots selectable directly, handle clicks via scene
            # dot.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            dot.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            dot.setZValue(self.z_value + 1) # Dots above component body

    def boundingRect(self) -> QRectF:
        # Expand bounding rect slightly to include dots if they protrude
        extra: float = DOT_SIZE / 2 + 2 # Add padding
        return QRectF(-extra, -extra, self.width + 2 * extra, self.height + 2 * extra)

    # Corrected paint signature with imported QStyleOptionGraphicsItem
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget]=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen: QPen = QPen(QColor(0, 0, 0), 1.5)
        brush: QBrush = QBrush(self.color) # Use QBrush

        # Check selection state from the option parameter
        # Need to import QStyle for State_Selected
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected) if option else self.isSelected()

        if is_selected or self.highlighted:
            pen = QPen(QColor(0, 100, 255), 2) # Blue highlight pen
            # Optional: Add a highlight brush effect
            highlight_brush: QBrush = QBrush(QColor(0, 150, 255, 60)) # Semi-transparent blue
            painter.setBrush(highlight_brush)
            # Draw highlight shape slightly inside the bounding rect for visual clarity
            # Use the component's main shape for highlighting
            highlight_rect = QRectF(0, 0, self.width, self.height).adjusted(1, 1, -1, -1)
            if self.shape_type == "rect":
                 painter.drawRoundedRect(highlight_rect, 4, 4) # Slightly smaller radius
            elif self.shape_type == "ellipse":
                 painter.drawEllipse(highlight_rect)

        painter.setPen(pen)
        painter.setBrush(brush) # Set the main component brush

        # Draw the main component body
        if self.shape_type == "rect":
            painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)
        elif self.shape_type == "ellipse":
            painter.drawEllipse(0, 0, self.width, self.height)
            # Draw polarity for voltage source inside ellipse
            center_x: float = self.width / 2
            plus_y: float = 8 # Y position for '+' sign elements
            minus_y: float = self.height - 8 # Y position for '-' sign elements
            sign_half_width: float = 5
            sign_half_height: float = 5
            # Plus sign (+)
            painter.drawLine(QPointF(center_x - sign_half_width, plus_y), QPointF(center_x + sign_half_width, plus_y)) # Horizontal bar
            painter.drawLine(QPointF(center_x, plus_y - sign_half_height), QPointF(center_x, plus_y + sign_half_height)) # Vertical bar
            # Minus sign (-)
            painter.drawLine(QPointF(center_x - sign_half_width, minus_y), QPointF(center_x + sign_half_width, minus_y)) # Horizontal bar


    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """Override to handle position changes and update lines."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            # Update paths of all connected lines
            for line in list(self.lines): # Iterate over copy in case set changes
                 if line and line.scene(): # Check if line still valid
                     line.update_path() # Call the updated method name
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.snap_to_grid:
             # Snap preview position during drag
             if isinstance(value, QPointF): # Check if value is QPointF
                 snapped_x = round(value.x() / GRID_SIZE) * GRID_SIZE
                 snapped_y = round(value.y() / GRID_SIZE) * GRID_SIZE
                 return QPointF(snapped_x, snapped_y)

        return super().itemChange(change, value)

    # Corrected mouseDoubleClickEvent signature with imported QGraphicsSceneMouseEvent
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Allow changing component value on double-click."""
        current_value: float = self.value
        prompt_title: str = ""
        prompt_label: str = ""
        unit: str = ""

        if self.component_type == "R":
            prompt_title = "Change Resistance"
            prompt_label = "Enter new resistance value (Ω):"
            unit = " Ω"
        elif self.component_type == "V":
            prompt_title = "Change Voltage"
            prompt_label = "Enter new voltage value (V):"
            unit = " V\n(+/-)" # Remind polarity

        if prompt_title:
            # Use parent widget (CircuitVisualizer) for the dialog if possible
            parent_widget = self.scene().views()[0].window() if self.scene() and self.scene().views() else None
            new_value, ok = QInputDialog.getDouble(parent_widget, prompt_title, prompt_label, current_value, 0)
            if ok:
                if self.component_type == "R" and new_value <= 0:
                     QMessageBox.warning(parent_widget, "Invalid Input", "Resistance must be positive.")
                     return

                self.value = new_value
                self.text_str = f"{self.name}\n{new_value}{unit}"
                self.text.setPlainText(self.text_str)
                # Recenter text if needed
                text_rect: QRectF = self.text.boundingRect()
                if self.shape_type == "rect":
                    self.text.setPos((self.width - text_rect.width()) / 2, (self.height - text_rect.height()) / 2)
                else: # Ellipse
                    self.text.setPos((self.width - text_rect.width()) / 2, (self.height - text_rect.height()) / 2)

                self.update() # Redraw the component with new text

        super().mouseDoubleClickEvent(event) # Pass event along

    # Corrected mousePressEvent signature with imported QGraphicsSceneMouseEvent
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse press for potential movement."""
        super().mousePressEvent(event)

    # Corrected mouseReleaseEvent signature with imported QGraphicsSceneMouseEvent
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse release after movement, snap to grid."""
        if self.snap_to_grid:
            # Final snap after releasing the mouse
            new_x = round(self.x() / GRID_SIZE) * GRID_SIZE
            new_y = round(self.y() / GRID_SIZE) * GRID_SIZE
            if self.pos() != QPointF(new_x, new_y):
                self.setPos(new_x, new_y) # This triggers itemChange -> update lines

        super().mouseReleaseEvent(event)

    def add_line(self, line: ConnectionLine) -> None:
        """Adds a connection line associated with this component."""
        self.lines.add(line)

    def remove_line(self, line: ConnectionLine) -> None:
        """Removes a connection line."""
        self.lines.discard(line) # Use discard to avoid errors if not found

    def remove_all_lines(self) -> None:
        """Removes all connection lines associated with this component from the scene."""
        if not self.scene(): return # Cannot remove if not in scene

        # Iterate over a copy of the set as we might modify it
        lines_to_remove = list(self.lines)
        for line in lines_to_remove:
            # Remove from the other component's set first
            comp1 = line.get_component1()
            comp2 = line.get_component2()
            other_comp = comp1 if comp2 == self else comp2
            if other_comp:
                other_comp.remove_line(line)

            # Remove from this component's set
            self.remove_line(line)

            # Remove from scene
            if line.scene() == self.scene():
                 self.scene().removeItem(line)


class CircuitView(QGraphicsView):
    """Custom QGraphicsView with panning and zooming."""
    def __init__(self, scene: QGraphicsScene, parent: Optional[QWidget]=None):
        super().__init__(scene, parent)
        self._panning: bool = False
        self._last_pan_point: QPointF = QPointF()

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Enable panning with ScrollHandDrag mode (usually middle mouse or Ctrl+LeftClick)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        # Set focus policy to accept keyboard events like Delete
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handles mouse wheel events for zooming."""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        # Check if Ctrl key is pressed for zooming (optional, common convention)
        # if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
        zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else zoom_out_factor
        self.scale(zoom_factor, zoom_factor)
        # else:
        #     # Allow default wheel event for scrolling if Ctrl not pressed
        #     super().wheelEvent(event)


# Change base class to QMainWindow
class CircuitVisualizer(QMainWindow):
    """Main application window for visualizing and analyzing circuits."""
    def __init__(self, parent: Optional[QWidget]=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle('Circuit Mesh Analyzer')
        self.setGeometry(100, 100, 1000, 750) # Increased height slightly for menu

        # --- Central Widget Setup ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout: QVBoxLayout = QVBoxLayout(self.central_widget) # Layout for the central widget

        # --- Graphics Scene and View ---
        self.scene: QGraphicsScene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 2000, 1500)
        self.view: CircuitView = CircuitView(self.scene, self.central_widget)
        self.layout.addWidget(self.view) # Add view to the central widget's layout

        # --- Grid ---
        self.draw_grid()

        # --- Buttons (can be kept or moved to a toolbar) ---
        self.button_layout: QGridLayout = QGridLayout()
        # Get standard icons
        add_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        analyze_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        clear_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)

        self.add_resistor_button: QPushButton = QPushButton(" Add Resistor (R)") # Text adjusted for icon
        self.add_voltage_button: QPushButton = QPushButton(" Add Voltage (V)") # Text adjusted for icon
        self.analyze_button: QPushButton = QPushButton(" Analyze")
        self.clear_button: QPushButton = QPushButton(" Clear All")

        # Set icons on buttons
        self.add_resistor_button.setIcon(add_icon)
        self.add_voltage_button.setIcon(add_icon) # Use same add icon for now
        self.analyze_button.setIcon(analyze_icon)
        self.clear_button.setIcon(clear_icon)
        self.add_resistor_button.setIconSize(ICON_SIZE)
        self.add_voltage_button.setIconSize(ICON_SIZE)
        self.analyze_button.setIconSize(ICON_SIZE)
        self.clear_button.setIconSize(ICON_SIZE)


        button_height: int = 35
        self.add_resistor_button.setFixedHeight(button_height)
        self.add_voltage_button.setFixedHeight(button_height)
        self.analyze_button.setFixedHeight(button_height)
        self.clear_button.setFixedHeight(button_height)

        button_style: str = """
            QPushButton {
                background-color: #e0e0e0; border: 1px solid #b0b0b0;
                padding: 5px; border-radius: 4px; font-size: 10pt;
                text-align: left; /* Align text left for icon */
                padding-left: 10px; /* Add padding for icon */
            }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #c0c0c0; }
        """
        self.add_resistor_button.setStyleSheet(button_style)
        self.add_voltage_button.setStyleSheet(button_style)
        self.analyze_button.setStyleSheet(button_style + "QPushButton { background-color: #c8e6c9; } QPushButton:hover { background-color: #b2dfdb; }") # Greenish
        self.clear_button.setStyleSheet(button_style + "QPushButton { background-color: #ffcdd2; } QPushButton:hover { background-color: #ef9a9a; }") # Reddish


        self.button_layout.addWidget(self.add_resistor_button, 0, 0)
        self.button_layout.addWidget(self.add_voltage_button, 0, 1)
        self.button_layout.addWidget(self.analyze_button, 1, 0)
        self.button_layout.addWidget(self.clear_button, 1, 1)
        self.layout.addLayout(self.button_layout) # Add buttons below the view

        # --- Results Area ---
        self.result_label: QLabel = QLabel("Circuit analysis results will appear here.")
        self.result_label.setStyleSheet("font: 10pt Arial; color: #333; padding: 5px; background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px;")
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.result_label.setFixedHeight(100) # Fixed height for results area
        self.layout.addWidget(self.result_label) # Add results below buttons

        # --- Menu Bar ---
        self._create_actions()
        self._create_menu_bar()

        # --- State Variables ---
        self.component_count: Dict[str, int] = {'R': 1, 'V': 1} # Track counts per type
        self.connecting_dot: Optional[QGraphicsEllipseItem] = None # The dot where connection starts
        self.temp_line: Optional[QGraphicsLineItem] = None # The line drawn while connecting

        # --- Connect Signals ---
        self.add_resistor_button.clicked.connect(self.add_resistor)
        self.add_voltage_button.clicked.connect(self.add_voltage)
        self.analyze_button.clicked.connect(self.analyze_circuit)
        self.clear_button.clicked.connect(self.clear_circuit)

        # Assign scene event handlers (no change needed here)
        self.scene.mousePressEvent = self.scene_mousePressEvent
        self.scene.mouseMoveEvent = self.scene_mouseMoveEvent
        self.scene.mouseReleaseEvent = self.scene_mouseReleaseEvent
        self.scene.keyPressEvent = self.scene_keyPressEvent

    def _create_actions(self) -> None:
        """Create QAction objects for menu items."""
        # File Actions
        self.exit_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), "&Exit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.setStatusTip("Exit the application")
        self.exit_action.triggered.connect(self.close) # QMainWindow has close()

        # Edit Actions (Mapped to existing button slots)
        self.add_resistor_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Add &Resistor", self)
        self.add_resistor_action.setShortcut("Ctrl+R")
        self.add_resistor_action.setStatusTip("Add a new resistor component")
        self.add_resistor_action.triggered.connect(self.add_resistor)

        self.add_voltage_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Add &Voltage Source", self)
        self.add_voltage_action.setShortcut("Ctrl+V")
        self.add_voltage_action.setStatusTip("Add a new voltage source component")
        self.add_voltage_action.triggered.connect(self.add_voltage)

        self.clear_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "&Clear Circuit", self)
        self.clear_action.setShortcut("Ctrl+Backspace")
        self.clear_action.setStatusTip("Clear all components and connections")
        self.clear_action.triggered.connect(self.clear_circuit)

        # Analyze Actions
        self.analyze_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "&Analyze Circuit", self)
        self.analyze_action.setShortcut("Ctrl+Return") # Or F5?
        self.analyze_action.setStatusTip("Perform mesh analysis on the circuit")
        self.analyze_action.triggered.connect(self.analyze_circuit)

        # Help Actions (Example)
        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("Show application information")
        self.about_action.triggered.connect(self.show_about_dialog)


    def _create_menu_bar(self) -> None:
        """Create the main menu bar and menus."""
        menu_bar = self.menuBar() # QMainWindow provides menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        # Add file actions here (e.g., Save, Load - not implemented)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.add_resistor_action)
        edit_menu.addAction(self.add_voltage_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.clear_action)
        # Add Undo/Redo actions here if implemented

        # Analyze Menu
        analyze_menu = menu_bar.addMenu("A&nalyze")
        analyze_menu.addAction(self.analyze_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.about_action)

    def show_about_dialog(self) -> None:
        """Placeholder for an About dialog."""
        QMessageBox.about(self, "About Circuit Mesh Analyzer",
                          "A simple circuit visualizer and mesh analysis tool.\n"
                          "Created with PyQt6 and NetworkX.")


    def draw_grid(self) -> None:
        """Draws a grid on the scene background."""
        scene_rect: QRectF = self.scene.sceneRect()
        grid_pen: QPen = QPen(QColor(220, 220, 220), 0.5) # Thinner pen
        grid_pen.setCosmetic(True) # Pen width independent of zoom

        # Find existing grid lines to remove them first
        grid_lines = [item for item in self.scene.items()
                      if isinstance(item, QGraphicsLineItem) and item.zValue() == -1000]
        for item in grid_lines:
            self.scene.removeItem(item)

        # Draw vertical lines
        start_x: float = round(scene_rect.left() / GRID_SIZE) * GRID_SIZE
        end_x: float = round(scene_rect.right() / GRID_SIZE) * GRID_SIZE
        x: float = start_x
        while x <= end_x:
            line = QGraphicsLineItem(x, scene_rect.top(), x, scene_rect.bottom())
            line.setPen(grid_pen)
            line.setZValue(-1000) # Ensure grid is behind everything
            self.scene.addItem(line)
            x += GRID_SIZE

        # Draw horizontal lines
        start_y: float = round(scene_rect.top() / GRID_SIZE) * GRID_SIZE
        end_y: float = round(scene_rect.bottom() / GRID_SIZE) * GRID_SIZE
        y: float = start_y
        while y <= end_y:
            line = QGraphicsLineItem(scene_rect.left(), y, scene_rect.right(), y)
            line.setPen(grid_pen)
            line.setZValue(-1000)
            self.scene.addItem(line)
            y += GRID_SIZE

    def add_component(self, component_type: str) -> Optional[CircuitComponent]:
        """Adds a component to the scene near the center of the current view."""
        if component_type not in ["R", "V"]:
            print(f"Error: Invalid component type requested: {component_type}")
            return None

        type_label: str = "Resistance (Ω)" if component_type == "R" else "Voltage (V)"
        name: str = f"{component_type}{self.component_count[component_type]}"

        value, ok = QInputDialog.getDouble(self, f"Add {component_type}", f"Enter {type_label} for {name}:", 1.0, 0) # Default 1.0

        if ok:
            if component_type == "R" and value <= 0:
                QMessageBox.warning(self, "Invalid Input", "Resistance must be positive.")
                return None # Indicate failure

            # Place near the center of the current view, snapped to grid
            center_point: QPointF = self.view.mapToScene(self.view.viewport().rect().center())
            x: float = round(center_point.x() / GRID_SIZE) * GRID_SIZE
            y: float = round(center_point.y() / GRID_SIZE) * GRID_SIZE

            # Check if position is occupied (simple check, might need refinement)
            check_rect = QRectF(x - GRID_SIZE / 4, y - GRID_SIZE / 4, GRID_SIZE / 2, GRID_SIZE / 2)
            items_at_pos = self.scene.items(check_rect)
            if any(isinstance(item, CircuitComponent) for item in items_at_pos):
                 # Try slightly offset position if center is occupied
                 x += GRID_SIZE
                 y += GRID_SIZE

            component = CircuitComponent(name, value, component_type, x, y)
            self.scene.addItem(component)
            self.component_count[component_type] += 1
            return component
        return None # Indicate cancellation

    def add_resistor(self) -> None:
        self.add_component("R")

    def add_voltage(self) -> None:
        self.add_component("V")

    def clear_circuit(self) -> None:
        """Clears all components and connections from the scene."""
        reply = QMessageBox.question(self, "Confirm Clear",
                                     "Are you sure you want to clear the entire circuit?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        # Remove all items properly except the background grid
        items_to_remove: List[QGraphicsItem] = []
        for item in self.scene.items():
             # Keep grid lines (identified by low ZValue), remove everything else
             if not (isinstance(item, QGraphicsLineItem) and item.zValue() == -1000):
                items_to_remove.append(item)

        for item in items_to_remove:
            self.scene.removeItem(item) # Let Qt handle cleanup

        # Reset state
        self.connecting_dot = None
        self.temp_line = None
        self.component_count = {'R': 1, 'V': 1}
        self.result_label.setText("Circuit cleared. Add components to begin.")
        # Grid remains

    # Corrected scene_keyPressEvent signature with imported QKeyEvent
    def scene_keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key presses, e.g., Delete key."""
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            selected_items: List[QGraphicsItem] = self.scene.selectedItems()
            if not selected_items:
                return # Nothing selected

            reply = QMessageBox.question(self, "Confirm Deletion",
                                         f"Delete {len(selected_items)} selected item(s)?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                # Make a copy because removing items can change selection
                items_to_delete = list(selected_items)
                for item in items_to_delete:
                    if isinstance(item, CircuitComponent):
                        # Remove lines connected *to this component* first
                        item.remove_all_lines() # Handles removing from scene and other comp
                        if item.scene(): # Check if still in scene before removing
                             self.scene.removeItem(item)
                    elif isinstance(item, ConnectionLine): # Check for ConnectionLine specifically
                        # Remove line from associated components and scene
                        comp1 = item.get_component1()
                        comp2 = item.get_component2()
                        if comp1: comp1.remove_line(item)
                        if comp2: comp2.remove_line(item)
                        # Ensure item is still in scene before removing (might be removed by component removal)
                        if item.scene():
                            self.scene.removeItem(item)
                    # Add handling for other deletable items if necessary
        else:
            # Pass event to default handler if not Delete key
            # The scene itself doesn't have a default keyPressEvent to call super on directly
            # We handle it here or ignore it.
            event.ignore() # Indicate event was not handled here if not delete


    # Corrected scene_mousePressEvent signature with imported QGraphicsSceneMouseEvent
    def scene_mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles mouse press on the scene to start connections or select items."""
        pos: QPointF = event.scenePos()
        # Find item directly under cursor, ensure transformation is identity for direct mapping
        item_at: Optional[QGraphicsItem] = self.scene.itemAt(pos, QTransform())

        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the item is one of our component dots
            is_dot = isinstance(item_at, QGraphicsEllipseItem)
            is_dot_on_component = is_dot and isinstance(item_at.parentItem(), CircuitComponent)

            if is_dot_on_component:
                # Clicked on a connection dot - start drawing a line
                self.connecting_dot = item_at # Assign the QGraphicsEllipseItem
                if self.connecting_dot: # Check if assignment was successful
                    self.connecting_dot.setBrush(QColor("yellow")) # Highlight starting dot
                    start_point: QPointF = self.connecting_dot.scenePos() + QPointF(DOT_SIZE / 2, DOT_SIZE / 2)
                    # Keep temp line as straight line for simplicity during drag
                    self.temp_line = QGraphicsLineItem(QLineF(start_point, start_point))
                    self.temp_line.setPen(QPen(QColor(0, 150, 255), 2, Qt.PenStyle.DashLine))
                    self.temp_line.setZValue(5) # Above components slightly
                    self.scene.addItem(self.temp_line)
                    event.accept() # Consume event so view doesn't pan
                else:
                     event.ignore() # Connecting dot was None? Ignore.
            else:
                # Clicked elsewhere, let the view handle selection/moving/panning
                 event.ignore() # Allow event propagation to the view

        else:
             # Pass other button presses (e.g., right-click for context menu)
             event.ignore() # Allow event propagation

    # Corrected scene_mouseMoveEvent signature with imported QGraphicsSceneMouseEvent
    def scene_mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles mouse movement for drawing connection lines or moving items."""
        if self.connecting_dot and self.temp_line:
            # Update the end point of the temporary line to follow the mouse
            start_point: QPointF = self.connecting_dot.scenePos() + QPointF(DOT_SIZE / 2, DOT_SIZE / 2)
            end_point: QPointF = event.scenePos()
            self.temp_line.setLine(QLineF(start_point, end_point))
            event.accept() # Consume event
        else:
            # Allow event propagation for view panning etc.
            event.ignore()

    # Corrected scene_mouseReleaseEvent signature with imported QGraphicsSceneMouseEvent
    def scene_mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles mouse release to finalize connections or item movement."""
        if self.connecting_dot and self.temp_line:
            # Connection drawing was in progress
            self.connecting_dot.setBrush(QColor("red")) # Reset starting dot color

            # Find item under mouse release position
            end_pos: QPointF = event.scenePos()
            # Use items() in a small rectangle around the end point for better hit detection
            tolerance: float = 5.0
            search_rect = QRectF(end_pos - QPointF(tolerance, tolerance), QSizeF(tolerance*2, tolerance*2))
            items_under_cursor: List[QGraphicsItem] = self.scene.items(search_rect)
            end_dot_item: Optional[QGraphicsEllipseItem] = None
            for item in items_under_cursor:
                 # Ensure it's an ellipse, part of a component, and not the starting dot
                 if isinstance(item, QGraphicsEllipseItem) and \
                    isinstance(item.parentItem(), CircuitComponent) and \
                    item != self.connecting_dot:
                     end_dot_item = item
                     break # Found a valid target dot

            # Check if released over a valid connection dot on a *different* component
            valid_connection: bool = False
            if end_dot_item:
                start_comp = self.connecting_dot.parentItem()
                end_comp = end_dot_item.parentItem()
                # Ensure components are valid CircuitComponent instances
                if isinstance(start_comp, CircuitComponent) and isinstance(end_comp, CircuitComponent):
                    if start_comp != end_comp: # Cannot connect component to itself (usually)
                        # Valid connection target found
                        # Check if this specific connection already exists
                        new_line = ConnectionLine(self.connecting_dot, end_dot_item) # Create potential new line
                        # Check against existing lines in the scene
                        existing_lines = [item for item in self.scene.items() if isinstance(item, ConnectionLine)]

                        connection_already_exists: bool = False
                        for existing_line in existing_lines:
                            # Use the __eq__ method defined in ConnectionLine
                            if new_line == existing_line:
                                connection_already_exists = True
                                break

                        if not connection_already_exists:
                            # Add the new orthogonal line (new_line object already created)
                            self.scene.addItem(new_line)
                            start_comp.add_line(new_line)
                            end_comp.add_line(new_line)
                            valid_connection = True
                        else:
                             QMessageBox.information(self, "Connection Exists", "These components are already connected between these points.")
                    else:
                         QMessageBox.warning(self, "Connection Error", "Cannot connect a component to itself.")

            # Clean up temporary line
            if self.temp_line and self.temp_line.scene(): # Check if it exists and is in the scene
                self.scene.removeItem(self.temp_line)
            self.temp_line = None
            self.connecting_dot = None
            event.accept() # Consume event

            if not valid_connection:
                # Connection failed or cancelled
                pass # Just cleaned up temp line

        else:
            # No connection was being drawn, allow event propagation for view etc.
            event.ignore()


    # --- Analysis Logic ---

    def _build_graph(self, components: List[CircuitComponent], connections: List[ConnectionLine]) -> Optional[nx.Graph]:
        """Builds the networkx graph representation of the circuit."""
        G = nx.Graph()
        # Use the dot item itself as the key for mapping, easier to manage
        node_map: Dict[QGraphicsEllipseItem, int] = {}
        node_counter: int = 0

        # Add nodes for each connection point (dot)
        for comp in components:
            if not comp.dot1 or not comp.dot2: # Check if dots exist
                print(f"Warning: Component {comp.name} has missing dots.")
                continue
            for dot in comp.dots:
                if dot not in node_map:
                    node_map[dot] = node_counter
                    # Store component and dot info on the node
                    G.add_node(node_counter, component=comp, dot=dot)
                    node_counter += 1

            # Add internal edge for the component itself
            if comp.dot1 in node_map and comp.dot2 in node_map:
                dot1_node_id = node_map[comp.dot1]
                dot2_node_id = node_map[comp.dot2]
                if dot1_node_id != dot2_node_id: # Ensure dots map to different nodes
                    G.add_edge(dot1_node_id, dot2_node_id, element=comp)
            else:
                 print(f"Warning: Could not find nodes for component {comp.name} dots during internal edge creation.")

        # Add edges for the wires (ConnectionLine)
        for line in connections:
            if line.dot1 and line.dot2 and line.dot1 in node_map and line.dot2 in node_map:
                dot1_node_id = node_map[line.dot1]
                dot2_node_id = node_map[line.dot2]
                if dot1_node_id != dot2_node_id:
                     # Add edge only if it doesn't already exist (e.g., from a component)
                     if not G.has_edge(dot1_node_id, dot2_node_id):
                         G.add_edge(dot1_node_id, dot2_node_id, element='wire')
            else:
                 # Use object IDs for logging if available
                 dot1_id = id(line.dot1) if line.dot1 else 'None'
                 dot2_id = id(line.dot2) if line.dot2 else 'None'
                 print(f"Warning: Could not find nodes for line between dots {dot1_id} and {dot2_id}")

        return G


    def analyze_circuit(self) -> None:
        """Performs mesh analysis on the circuit drawn in the scene."""
        self.result_label.setText("Analyzing circuit...")
        QApplication.processEvents() # Update UI to show message

        components: List[CircuitComponent] = [item for item in self.scene.items() if isinstance(item, CircuitComponent)]
        connections: List[ConnectionLine] = [item for item in self.scene.items() if isinstance(item, ConnectionLine)]

        if not components:
            QMessageBox.warning(self, "Analysis Error", "No components in the circuit.")
            self.result_label.setText("Analysis Error: No components found.")
            return

        # Basic validation: Check for at least one voltage source?
        if not any(comp.component_type == 'V' for comp in components):
             QMessageBox.warning(self, "Analysis Warning", "No voltage sources found in the circuit. Analysis might yield zero currents.")
             # Continue analysis, might be valid if analyzing passive network properties

        if not connections and len(components) > 1: # Allow single component analysis? No.
             QMessageBox.warning(self, "Analysis Error", "No connections found. Components must be wired together.")
             self.result_label.setText("Analysis Error: No connections found.")
             return

        # --- Build Graph ---
        G = self._build_graph(components, connections)
        if G is None or G.number_of_nodes() == 0:
            QMessageBox.critical(self, "Analysis Error", "Failed to build circuit graph.")
            self.result_label.setText("Analysis Error: Graph building failed.")
            return

        # --- Check Connectivity ---
        try:
            # Ensure graph has edges before checking connectivity if nodes > 1
            if G.number_of_nodes() > 1 and G.number_of_edges() == 0:
                 QMessageBox.warning(self, "Analysis Error", "Components exist but are not connected.")
                 self.result_label.setText("Analysis Error: Components not connected.")
                 return
            # Check connectivity only if graph has nodes
            if G.number_of_nodes() > 0 and not nx.is_connected(G):
                 num_subgraphs = len(list(nx.connected_components(G)))
                 QMessageBox.warning(self, "Analysis Error", f"Circuit is not fully connected. Found {num_subgraphs} separate parts.")
                 self.result_label.setText(f"Analysis Error: Circuit not fully connected ({num_subgraphs} parts).")
                 return
        except Exception as e:
             QMessageBox.critical(self, "Analysis Error", f"Error checking connectivity: {e}")
             self.result_label.setText(f"Analysis Error: Connectivity check failed ({e}).")
             return

        # --- Find Fundamental Cycles (Meshes) ---
        try:
            # Ensure graph has edges before finding cycles
            if G.number_of_edges() == 0:
                 QMessageBox.warning(self, "Analysis Info", "Circuit has no connections (edges). Cannot perform mesh analysis.")
                 self.result_label.setText("Analysis Info: No connections found.")
                 return
            mesh_basis_nodes: List[List[int]] = nx.cycle_basis(G)
        except nx.NetworkXNoCycle:
             QMessageBox.warning(self, "Analysis Info", "The circuit contains no closed loops (meshes). Cannot perform mesh analysis.")
             self.result_label.setText("Analysis Info: No closed loops (meshes) found.")
             return
        except Exception as e:
             QMessageBox.critical(self, "Analysis Error", f"Error finding meshes: {e}")
             self.result_label.setText(f"Analysis Error: Could not find meshes ({e}).")
             return

        if not mesh_basis_nodes:
             QMessageBox.warning(self, "Analysis Info", "No fundamental meshes found (circuit might be a tree structure or disconnected). Mesh analysis requires loops.")
             self.result_label.setText("Analysis Info: No closed loops (meshes) found.")
             return

        num_meshes: int = len(mesh_basis_nodes)
        print(f"Found {num_meshes} potential meshes (cycles): {mesh_basis_nodes}")

        # --- Set up Mesh Equations (KVL) ---
        resistance_matrix = np.zeros((num_meshes, num_meshes))
        voltage_vector = np.zeros(num_meshes)

        # Map edges to the meshes they belong to
        edge_meshes: Dict[frozenset, List[int]] = {} # key: frozenset(u,v), value: list of mesh indices
        mesh_edges_ordered: List[List[Tuple[int, int]]] = [] # List of lists of edges for each mesh, ordered

        for i, mesh_nodes in enumerate(mesh_basis_nodes):
            ordered_edges = []
            for k in range(len(mesh_nodes)):
                u = mesh_nodes[k]
                v = mesh_nodes[(k + 1) % len(mesh_nodes)] # Next node in cycle
                if G.has_edge(u,v):
                    edge = frozenset([u, v])
                    ordered_edges.append((u,v))
                    if edge not in edge_meshes: edge_meshes[edge] = []
                    edge_meshes[edge].append(i)
                else:
                    print(f"Warning: Edge ({u}, {v}) from cycle basis not found directly in graph G for mesh {i}.")
            mesh_edges_ordered.append(ordered_edges)

        # --- Populate Matrices ---
        try:
            R_temp = np.zeros((num_meshes, num_meshes))
            V_temp = np.zeros(num_meshes)
            # Create inverse map from node ID to dot item (needed for polarity check)
            node_to_dot_map: Dict[int, QGraphicsEllipseItem] = {node_id: data['dot']
                                                                for node_id, data in G.nodes(data=True) if 'dot' in data}

            for i in range(num_meshes): # For each mesh equation
                for u, v in mesh_edges_ordered[i]: # Iterate through ordered edges in this mesh
                    edge_key = frozenset([u, v])
                    edge_data = G.get_edge_data(u, v)
                    if edge_data is None: continue

                    element = edge_data.get('element', None)

                    if isinstance(element, CircuitComponent):
                        comp = element
                        # Get component's actual dot items
                        comp_dot1 = comp.dot1
                        comp_dot2 = comp.dot2
                        if not comp_dot1 or not comp_dot2: continue # Skip if component dots invalid

                        # Map the actual component dots back to the node IDs used in this edge (u, v)
                        # This is crucial for determining direction correctly
                        node_id_for_comp_dot1 = None
                        node_id_for_comp_dot2 = None
                        # Find the node IDs corresponding to the component's specific dots
                        for node_id, dot_item in node_to_dot_map.items():
                            if dot_item == comp_dot1: node_id_for_comp_dot1 = node_id
                            if dot_item == comp_dot2: node_id_for_comp_dot2 = node_id
                            # Optimization: break if both found
                            if node_id_for_comp_dot1 is not None and node_id_for_comp_dot2 is not None:
                                break

                        if node_id_for_comp_dot1 is None or node_id_for_comp_dot2 is None:
                             print(f"Error: Could not map component {comp.name} dots back to graph nodes {u}, {v}.")
                             continue # Cannot determine direction

                        # Determine mesh current direction (u -> v) relative to component definition (dot1 -> dot2)
                        mesh_current_direction = 0
                        # Check if the edge (u,v) represents the component's internal connection
                        # in either direction
                        is_comp_edge_fwd = (u, v) == (node_id_for_comp_dot1, node_id_for_comp_dot2)
                        is_comp_edge_rev = (u, v) == (node_id_for_comp_dot2, node_id_for_comp_dot1)

                        if is_comp_edge_fwd: mesh_current_direction = 1
                        elif is_comp_edge_rev: mesh_current_direction = -1
                        else:
                             # This edge (u,v) is part of the mesh, but it's NOT the direct connection
                             # between the component's dots (e.g., it's a wire connected to the component).
                             # The component's contribution is handled only when processing its specific edge.
                             continue # Skip contribution for this edge


                        # Apply KVL based on component type
                        if comp.component_type == 'R':
                            R_temp[i, i] += comp.value
                            shared_mesh_indices = edge_meshes.get(edge_key, [])
                            for j in shared_mesh_indices:
                                if i != j: R_temp[i, j] -= comp.value
                        elif comp.component_type == 'V':
                            # Voltage rise is dot2 (-) -> dot1 (+)
                            if mesh_current_direction == 1: V_temp[i] -= comp.value # Current matches dot1->dot2 (drop)
                            elif mesh_current_direction == -1: V_temp[i] += comp.value # Current matches dot2->dot1 (rise)
                            # else: mesh_current_direction was 0 - error already printed

                    elif element == 'wire': pass # Wires have zero impedance

            # Finalize matrices
            resistance_matrix = (R_temp + R_temp.T) / 2
            for k in range(num_meshes): resistance_matrix[k,k] = R_temp[k,k]
            voltage_vector = V_temp

        except Exception as e:
             QMessageBox.critical(self, "Analysis Error", f"Error populating matrices: {e}")
             self.result_label.setText(f"Analysis Error: Matrix population failed ({e}).")
             import traceback
             traceback.print_exc()
             return

        # --- Check for Matrix Singularity and Solve ---
        print("Final Resistance Matrix (R):\n", resistance_matrix)
        print("Final Voltage Vector (V):\n", voltage_vector)

        try:
            determinant = np.linalg.det(resistance_matrix)
            print(f"Matrix Determinant: {determinant}")
            if abs(determinant) < 1e-9:
                 QMessageBox.critical(self, "Analysis Error", "Circuit configuration leads to a singular matrix (determinant is near zero). Check for issues like parallel voltage sources or short circuits.")
                 self.result_label.setText("Analysis Error: Singular matrix (det ≈ 0). Circuit unsolvable.")
                 return

            mesh_current_values: np.ndarray = np.linalg.solve(resistance_matrix, voltage_vector)

            # --- Format and Display Results ---
            result_text = "Mesh Analysis Results:\n"
            result_text += "-" * 25 + "\n"
            for i, current in enumerate(mesh_current_values):
                 mesh_name = f"Mesh {i+1}"
                 result_text += f"{mesh_name}: {current:.4f} A\n"

            self.result_label.setText(result_text)
            print("Calculated Mesh Currents:", mesh_current_values)

        except np.linalg.LinAlgError as e:
            QMessageBox.critical(self, "Analysis Error", f"Could not solve the linear equations (LinAlgError: {e}). The matrix might be singular or ill-conditioned.")
            self.result_label.setText(f"Analysis Error: Could not solve equations (LinAlgError: {e}).")
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", f"An unexpected error occurred during solving: {e}")
            self.result_label.setText(f"Analysis Error: Solver failed ({e}).")
            import traceback
            traceback.print_exc()

# --- Main Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # app.setStyle('Fusion') # Optional styling
    ex = CircuitVisualizer()
    ex.show()
    sys.exit(app.exec())
