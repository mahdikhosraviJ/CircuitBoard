import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                            QGraphicsScene, QToolBar, QGraphicsLineItem,
                            QGraphicsRectItem, QGraphicsEllipseItem, QMenu)
from PyQt6.QtCore import Qt, QPointF, QLineF, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter


class Component:
    BATTERY = 1
    RESISTOR = 2
    WIRE = 3
    NODE = 4


class CircuitBuilder(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Grid Circuit Builder")
        self.setGeometry(100, 100, 1000, 800)
        
        self.current_component = Component.WIRE
        self.drawing_wire = False
        self.wire_start = None
        self.temp_wire = None
        self.components = []
        self.connections = []
        self.grid_size = 20
        self.show_grid = True
        
        self.initUI()
        
    def initUI(self):
        # Create graphics view and scene
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setCentralWidget(self.view)
        
        # Create toolbar
        self.toolbar = QToolBar("Tools")
        self.addToolBar(self.toolbar)
        
        # Add toolbar buttons
        self.toolbar.addAction("Wire", lambda: self.set_component(Component.WIRE))
        self.toolbar.addAction("Resistor", lambda: self.set_component(Component.RESISTOR))
        self.toolbar.addAction("Battery", lambda: self.set_component(Component.BATTERY))
        self.toolbar.addAction("Node", lambda: self.set_component(Component.NODE))
        self.toolbar.addAction("Toggle Grid", self.toggle_grid)
        self.toolbar.addAction("Clear", self.clear_scene)
        
        # Context menu
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Set up scene
        self.scene.setSceneRect(-500, -400, 1000, 800)
        self.draw_grid()
        
    def draw_grid(self):
        if not self.show_grid:
            return
            
        pen = QPen(QColor(200, 200, 200), 1)
        rect = self.scene.sceneRect()
        
        # Draw vertical lines
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        for x in range(left, int(rect.right()), self.grid_size):
            self.scene.addLine(x, rect.top(), x, rect.bottom(), pen)
            
        # Draw horizontal lines
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        for y in range(top, int(rect.bottom()), self.grid_size):
            self.scene.addLine(rect.left(), y, rect.right(), y, pen)
            
    def toggle_grid(self):
        self.show_grid = not self.show_grid
        # Remove all grid lines
        for item in self.scene.items():
            if hasattr(item, 'is_grid') and item.is_grid:
                self.scene.removeItem(item)
        if self.show_grid:
            self.draw_grid()
            
    def snap_to_grid(self, point):
        x = round(point.x() / self.grid_size) * self.grid_size
        y = round(point.y() / self.grid_size) * self.grid_size
        return QPointF(x, y)
        
    def set_component(self, component_type):
        self.current_component = component_type
        self.drawing_wire = False
        
    def clear_scene(self):
        self.scene.clear()
        self.components = []
        self.connections = []
        if self.show_grid:
            self.draw_grid()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.snap_to_grid(self.view.mapToScene(event.pos()))
            
            if self.current_component == Component.WIRE:
                self.drawing_wire = True
                self.wire_start = pos
            elif self.current_component == Component.RESISTOR:
                self.add_resistor(pos)
            elif self.current_component == Component.BATTERY:
                self.add_battery(pos)
            elif self.current_component == Component.NODE:
                self.add_node(pos)
                
    def mouseMoveEvent(self, event):
        if self.drawing_wire and self.wire_start:
            pos = self.snap_to_grid(self.view.mapToScene(event.pos()))
            self.draw_temp_wire(self.wire_start, pos)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing_wire:
            pos = self.snap_to_grid(self.view.mapToScene(event.pos()))
            if pos != self.wire_start:  # Don't create zero-length wires
                self.add_wire(self.wire_start, pos)
            self.drawing_wire = False
            self.wire_start = None
            # Remove temporary wire
            if self.temp_wire:
                self.scene.removeItem(self.temp_wire)
                self.temp_wire = None
                
    def draw_temp_wire(self, start, end):
        # Remove previous temporary wire
        if self.temp_wire:
            self.scene.removeItem(self.temp_wire)
            
        # Draw new temporary wire
        self.temp_wire = QGraphicsLineItem(QLineF(start, end))
        self.temp_wire.setPen(QPen(Qt.GlobalColor.darkGray, 2, Qt.PenStyle.DashLine))
        self.scene.addItem(self.temp_wire)
        
    def add_wire(self, start, end):
        line = QGraphicsLineItem(QLineF(start, end))
        line.setPen(QPen(Qt.GlobalColor.black, 3))
        self.scene.addItem(line)
        self.components.append(("wire", start, end))
        
        # Add connections
        self.add_connection(start)
        self.add_connection(end)
        
    def add_connection(self, point):
        # Check if there's already a connection at this point
        for conn in self.connections:
            if conn['point'] == point:
                return
                
        # Create a new connection
        self.connections.append({
            'point': point,
            'components': []
        })
        
    def add_resistor(self, pos):
        # Create resistor symbol (rectangle)
        resistor = QGraphicsRectItem(QRectF(-20, -10, 40, 20))
        resistor.setPos(pos)
        resistor.setPen(QPen(Qt.GlobalColor.black, 2))
        resistor.setBrush(QBrush(Qt.GlobalColor.white))
        
        # Add connection points
        left_conn = QPointF(pos.x() - 20, pos.y())
        right_conn = QPointF(pos.x() + 20, pos.y())
        
        # Draw small circles at connection points
        left_dot = QGraphicsEllipseItem(-3, -3, 6, 6, resistor)
        left_dot.setPos(left_conn - pos)
        left_dot.setBrush(QBrush(Qt.GlobalColor.black))
        
        right_dot = QGraphicsEllipseItem(-3, -3, 6, 6, resistor)
        right_dot.setPos(right_conn - pos)
        right_dot.setBrush(QBrush(Qt.GlobalColor.black))
        
        self.scene.addItem(resistor)
        self.components.append(("resistor", pos, left_conn, right_conn))
        
        # Add connections
        self.add_connection(left_conn)
        self.add_connection(right_conn)
        
    def add_battery(self, pos):
        # Create battery group
        battery = QGraphicsRectItem(QRectF(-25, -40, 50, 80))
        battery.setPos(pos)
        battery.setPen(QPen(Qt.GlobalColor.transparent))
        
        # Create battery symbol (two parallel lines of different lengths)
        long_line = QGraphicsLineItem(-15, -30, -15, 30, battery)
        short_line = QGraphicsLineItem(15, -20, 15, 20, battery)
        
        # Add connection points
        top_conn = QPointF(pos.x(), pos.y() - 40)
        bottom_conn = QPointF(pos.x(), pos.y() + 40)
        
        # Draw small circles at connection points
        top_dot = QGraphicsEllipseItem(-3, -3, 6, 6, battery)
        top_dot.setPos(0, -40)
        top_dot.setBrush(QBrush(Qt.GlobalColor.black))
        
        bottom_dot = QGraphicsEllipseItem(-3, -3, 6, 6, battery)
        bottom_dot.setPos(0, 40)
        bottom_dot.setBrush(QBrush(Qt.GlobalColor.black))
        
        # Add plus and minus signs
        plus_h = QGraphicsLineItem(-25, 0, -5, 0, battery)
        plus_v = QGraphicsLineItem(-15, -10, -15, 10, battery)
        minus = QGraphicsLineItem(5, -10, 25, -10, battery)
        
        long_line.setPen(QPen(Qt.GlobalColor.black, 4))
        short_line.setPen(QPen(Qt.GlobalColor.black, 4))
        
        self.scene.addItem(battery)
        self.components.append(("battery", pos, top_conn, bottom_conn))
        
        # Add connections
        self.add_connection(top_conn)
        self.add_connection(bottom_conn)
        
    def add_node(self, pos):
        # Create connection node
        node = QGraphicsEllipseItem(-5, -5, 10, 10)
        node.setPos(pos)
        node.setPen(QPen(Qt.GlobalColor.black, 1))
        node.setBrush(QBrush(Qt.GlobalColor.black))
        self.scene.addItem(node)
        self.components.append(("node", pos))
        self.add_connection(pos)
        
    def show_context_menu(self, pos):
        scene_pos = self.view.mapToScene(pos)
        menu = QMenu(self)
        
        # Check if we clicked on a component
        clicked_item = None
        for item in self.scene.items(scene_pos):
            if not isinstance(item, QGraphicsLineItem) or item not in [c[0] for c in self.components if c[0] == 'wire']:
                clicked_item = item
                break
                
        if clicked_item:
            menu.addAction("Delete", lambda: self.delete_component(clicked_item))
            
        menu.exec(self.view.mapToGlobal(pos))
        
    def delete_component(self, component):
        # Find and remove the component from our lists
        for i, comp in enumerate(self.components):
            if comp[0] == "wire" and component in self.scene.items():
                if (comp[1] == component.line().p1() and comp[2] == component.line().p2()) or \
                   (comp[1] == component.line().p2() and comp[2] == component.line().p1()):
                    self.components.pop(i)
                    break
            elif comp[0] in ["resistor", "battery", "node"] and component in self.scene.items():
                if comp[1] == component.pos():
                    self.components.pop(i)
                    break
                    
        # Remove from scene
        self.scene.removeItem(component)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CircuitBuilder()
    window.show()
    sys.exit(app.exec())
