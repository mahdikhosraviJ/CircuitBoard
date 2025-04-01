import pygame
import sys
import math

# تنظیمات رنگ‌ها
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
LIGHT_BLUE = (173, 216, 230)

# تنظیمات اولیه پنجره
INIT_WIDTH = 1280
INIT_HEIGHT = 800
WORKSPACE_PADDING = 20
FPS = 60

GRID_SIZE = 128
CELL_SIZE = 20  # Initial cell size
MIN_CELL_SIZE = 10
MAX_CELL_SIZE = 40

pygame.init()
screen = pygame.display.set_mode((INIT_WIDTH, INIT_HEIGHT))
pygame.display.set_caption("Circuit Simulator Pro")
clock = pygame.time.Clock()

class Component:
    def __init__(self, x, y, type_, value=0):
        self.x = x
        self.y = y
        self.type = type_
        self.value = value
        self.nodes = []
        self.selected = False
        self.editing = False
        self.temp_value = str(value)
        self.context_menu_active = False
        self.context_menu_rect = None
        self.update_nodes()
    
    def update_nodes(self):
        self.nodes = []
        if self.type == "battery":
            self.nodes = [(self.x, self.y-40), (self.x, self.y+40)]
        elif self.type == "resistor":
            self.nodes = [(self.x-40, self.y), (self.x+40, self.y)]
    
    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.update_nodes()
    
    def edit_value(self, key):
        if key == pygame.K_RETURN:
            try:
                new_value = float(self.temp_value)
                if new_value > 0:
                    self.value = new_value
                self.editing = False
            except ValueError:
                self.temp_value = str(self.value)
        elif key == pygame.K_BACKSPACE:
            self.temp_value = self.temp_value[:-1]
        elif key in [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                    pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9,
                    pygame.K_PERIOD]:
            self.temp_value += pygame.key.name(key)

    def draw(self):
        
        color = RED if self.selected else (GREEN if self.type == "battery" else BLUE)
        if self.type == "battery":
            pygame.draw.rect(screen, color, (self.x-15, self.y-30, 30, 60))
            pygame.draw.line(screen, BLACK, (self.x, self.y-30), (self.x, self.y+30), 3)
        elif self.type == "resistor":
            pygame.draw.rect(screen, color, (self.x-20, self.y-10, 40, 20))
            pygame.draw.line(screen, BLACK, (self.x-30, self.y), (self.x+30, self.y), 3)
        
        # Draw value or editing text
        if self.editing:
            text = self.temp_value + "|"
        else:
            text = f"{self.value}{'V' if self.type == 'battery' else 'Ω'}"
        self.draw_value(text)
    
    def draw_value(self, text):
        font = pygame.font.SysFont('tahoma', 14)
        text_surf = font.render(text, True, BLACK)
        text_rect = text_surf.get_rect(center=(self.x, self.y))
        screen.blit(text_surf, text_rect)
    
    def show_context_menu(self, screen, cell_size):
        if not self.context_menu_active:
            return
            
        menu_width = 120
        menu_height = 80
        menu_x = self.x + 20
        menu_y = self.y - 40
        
        self.context_menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        pygame.draw.rect(screen, WHITE, self.context_menu_rect)
        pygame.draw.rect(screen, BLACK, self.context_menu_rect, 2)
        
        font = pygame.font.SysFont('tahoma', 12)
        unit = "V" if self.type == "battery" else "Ω"
        text = f"Value: {self.value}{unit}"
        text_surf = font.render(text, True, BLACK)
        screen.blit(text_surf, (menu_x + 10, menu_y + 10))
        
        # Edit button
        edit_rect = pygame.Rect(menu_x + 10, menu_y + 40, 100, 25)
        pygame.draw.rect(screen, LIGHT_BLUE, edit_rect)
        edit_text = font.render("Edit Value", True, BLACK)
        screen.blit(edit_text, (edit_rect.x + 10, edit_rect.y + 5))
        
        return edit_rect

class Wire:
    def __init__(self, start_node, end_node):
        self.start = start_node
        self.end = end_node
        self.electrons = []
    
    def update_position(self, old_pos, new_pos):
        if self.start == old_pos:
            self.start = new_pos
        if self.end == old_pos:
            self.end = new_pos
    
    def draw(self):
        pygame.draw.line(screen, BLACK, self.start, self.end, 3)

class TextInput:
    def __init__(self, x, y, w, h, default_text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = default_text
        self.active = False

class Button:
    def __init__(self, x, y, w, h, text, color, hover_color=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color or color
    
    def draw(self, mouse_pos):
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        font = pygame.font.SysFont('tahoma', 20)
        text_surf = font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

class CircuitSimulator:
    def __init__(self):
        self.components = []
        self.wires = []
        self.current_tool = None
        self.simulation_running = False
        self.current_screen = "menu"
        self.dragging = None
        self.wire_start = None
        self.selected_node = None
        self.settings = {
            'width': INIT_WIDTH,
            'height': INIT_HEIGHT
        }
        self.tooltip_text = None
        self.tooltip_timer = 0
        self.selected_component = None
        self.cell_size = CELL_SIZE
        self.offset_x = 0
        self.offset_y = 0
        
        self.menu_buttons = []
        self.tool_buttons = []
        self.control_buttons = []
        self.settings_inputs = []
        self.apply_btn = None
        self.zoom_buttons = [
            Button(self.settings['width'] - 180, self.settings['height'] - 90, 80, 30, "Zoom +", LIGHT_BLUE),
            Button(self.settings['width'] - 90, self.settings['height'] - 90, 80, 30, "Zoom -", LIGHT_BLUE)
        ]
        self.update_button_positions()

    def update_button_positions(self):
        w = self.settings['width']
        h = self.settings['height']
        
        # Menu buttons remain unchanged
        self.menu_buttons = [
            Button(w//2-150, h//2-100, 300, 60, "New Circuit", LIGHT_BLUE, DARK_GRAY),
            Button(w//2-150, h//2-20, 300, 60, "Settings", LIGHT_BLUE, DARK_GRAY),
            Button(w//2-150, h//2+60, 300, 60, "Exit", LIGHT_BLUE, DARK_GRAY)
        ]
        
        # Create toolbar at top
        toolbar_height = 60
        button_size = 50
        spacing = 20
        start_x = w//2 - (button_size * 3 + spacing * 2)//2  # Center the toolbar
        
        self.tool_buttons = [
            Button(start_x, 5, button_size, button_size, "Battery", LIGHT_BLUE, DARK_GRAY),
            Button(start_x + button_size + spacing, 5, button_size, button_size, "Resistor", LIGHT_BLUE, DARK_GRAY),  
            Button(start_x + (button_size + spacing) * 2, 5, button_size, button_size, "Wire", LIGHT_BLUE, DARK_GRAY)
        ]
        
        # Control buttons - bottom right
        self.control_buttons = [
            Button(w - 180, h - 70, 160, 30, "Run/Stop", LIGHT_BLUE, DARK_GRAY),
            Button(w - 180, h - 35, 160, 30, "Clear All", LIGHT_BLUE, DARK_GRAY)
        ]

        # Settings inputs remain unchanged
        self.settings_inputs = [
            TextInput(w//2-100, h//2-50, 200, 40, str(w)),
            TextInput(w//2-100, h//2+10, 200, 40, str(h))
        ]
        self.apply_btn = Button(w//2-60, h//2+70, 120, 40, "Apply", LIGHT_BLUE, DARK_GRAY)

    def screen_to_grid(self, screen_x, screen_y):
        grid_x = (screen_x - WORKSPACE_PADDING - self.offset_x) // self.cell_size
        grid_y = (screen_y - 60 - self.offset_y) // self.cell_size
        return grid_x, grid_y

    def grid_to_screen(self, grid_x, grid_y):
        screen_x = grid_x * self.cell_size + WORKSPACE_PADDING + self.offset_x
        screen_y = grid_y * self.cell_size + 60 + self.offset_y
        return screen_x, screen_y

    def draw_grid(self):
        workspace_rect = pygame.Rect(WORKSPACE_PADDING, 60, 
                                   self.settings['width']-2*WORKSPACE_PADDING, 
                                   self.settings['height']-160)
        
        # Draw background
        pygame.draw.rect(screen, WHITE, workspace_rect)
        
        # Draw grid lines
        for x in range(GRID_SIZE + 1):
            screen_x = x * self.cell_size + WORKSPACE_PADDING + self.offset_x
            if screen_x < workspace_rect.right and screen_x > workspace_rect.left:
                pygame.draw.line(screen, GRAY, 
                               (screen_x, workspace_rect.top),
                               (screen_x, workspace_rect.bottom))
                
        for y in range(GRID_SIZE + 1):
            screen_y = y * self.cell_size + 60 + self.offset_y
            if screen_y < workspace_rect.bottom and screen_y > workspace_rect.top:
                pygame.draw.line(screen, GRAY,
                               (workspace_rect.left, screen_y),
                               (workspace_rect.right, screen_y))

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if self.selected_component and self.selected_component.editing:
                    self.selected_component.edit_value(event.key)
                elif event.key == pygame.K_DELETE and self.selected_component:
                    self.components.remove(self.selected_component)
                    self.selected_component = None
                elif event.key == pygame.K_RETURN and self.selected_component:
                    self.selected_component.editing = True
                    self.selected_component.temp_value = str(self.selected_component.value)
                elif event.key == pygame.K_ESCAPE:
                    self.current_screen = "menu"
                    self.resize_window(self.settings['width'], self.settings['height'])
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check zoom buttons
                    for btn in self.zoom_buttons:
                        if btn.rect.collidepoint(mouse_pos):
                            if btn.text == "Zoom +":
                                self.cell_size = min(self.cell_size + 5, MAX_CELL_SIZE)
                            else:
                                self.cell_size = max(self.cell_size - 5, MIN_CELL_SIZE)
                            return
                    
                    # Check component context menus
                    for comp in self.components:
                        if comp.context_menu_active:
                            edit_rect = comp.show_context_menu(screen, self.cell_size)
                            if edit_rect and edit_rect.collidepoint(mouse_pos):
                                comp.editing = True
                                comp.temp_value = str(comp.value)
                                comp.context_menu_active = False
                                return
                    
                    if self.current_screen == "menu":
                        for btn in self.menu_buttons:
                            if btn.rect.collidepoint(mouse_pos):
                                if btn.text == "New Circuit":
                                    self.current_screen = "main"
                                elif btn.text == "Settings":
                                    self.current_screen = "settings"
                                elif btn.text == "Exit":
                                    pygame.quit()
                                    sys.exit()
                    
                    elif self.current_screen == "settings":
                        for inp in self.settings_inputs:
                            if inp.rect.collidepoint(mouse_pos):
                                inp.active = True
                            else:
                                inp.active = False
                        
                        if self.apply_btn.rect.collidepoint(mouse_pos):
                            try:
                                new_width = int(self.settings_inputs[0].text)
                                new_height = int(self.settings_inputs[1].text)
                                if 800 <= new_width <= 1920 and 600 <= new_height <= 1080:
                                    self.resize_window(new_width, new_height)
                            except ValueError:
                                pass
                    
                    elif self.current_screen == "main":
                        for btn in self.control_buttons + self.tool_buttons:
                            if btn.rect.collidepoint(mouse_pos):
                                if btn.text == "Run/Stop":
                                    self.simulation_running = not self.simulation_running
                                elif btn.text == "Clear All":
                                    self.components = []
                                    self.wires = []
                                else:
                                    self.current_tool = btn.text.split()[0].lower()
                        
                        workspace_rect = pygame.Rect(WORKSPACE_PADDING, 60, 
                                                    self.settings['width']-2*WORKSPACE_PADDING, 
                                                    self.settings['height']-160)
                        if workspace_rect.collidepoint(mouse_pos):
                            if self.current_tool == "wire":
                                node = self.find_near_node(mouse_pos)
                                if node:
                                    if not self.wire_start:
                                        self.wire_start = node
                                    else:
                                        if self.validate_wire_connection(self.wire_start, node):
                                            self.wires.append(Wire(self.wire_start, node))
                                        self.wire_start = None
                            else:
                                component_clicked = False
                                for comp in self.components:
                                    if (comp.x-40 < mouse_pos[0] < comp.x+40 and 
                                        comp.y-40 < mouse_pos[1] < comp.y+40):
                                        self.dragging = comp
                                        component_clicked = True
                                        break
                                
                                if not component_clicked and self.current_tool in ["battery", "resistor"]:
                                    value = 9 if self.current_tool == "battery" else 100
                                    new_comp = Component(*mouse_pos, self.current_tool, value)
                                    self.components.append(new_comp)
                                    self.current_tool = None
                
                elif event.button == 3:  # Right click
                    # Toggle context menu
                    for comp in self.components:
                        if (comp.x-40 < mouse_pos[0] < comp.x+40 and 
                            comp.y-40 < mouse_pos[1] < comp.y+40):
                            comp.context_menu_active = not comp.context_menu_active
                            # Deactivate other menus
                            for other in self.components:
                                if other != comp:
                                    other.context_menu_active = False
                            break
            
            if event.type == pygame.MOUSEBUTTONUP:
                self.dragging = None
            
            if event.type == pygame.MOUSEMOTION and self.dragging:
                dx, dy = event.rel
                self.dragging.move(dx, dy)
                for wire in self.wires:
                    for node in self.dragging.nodes:
                        wire.update_position(node, (node[0]+dx, node[1]+dy))
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.selected_component = None
                for comp in self.components:
                    if (comp.x-40 < mouse_pos[0] < comp.x+40 and 
                        comp.y-40 < mouse_pos[1] < comp.y+40):
                        self.selected_component = comp
                        comp.selected = True
                    else:
                        comp.selected = False
                        comp.editing = False

    def resize_window(self, width, height):
        global screen
        self.settings.update({'width': width, 'height': height})
        screen = pygame.display.set_mode((width, height))
        self.update_button_positions()
        pygame.display.update()

    def find_near_node(self, pos):
        for comp in self.components:
            for node in comp.nodes:
                if math.dist(pos, node) < 15:
                    return node
        return None

    def validate_wire_connection(self, start_node, end_node):
        if start_node == end_node:
            return False
        
        # Check if wire already exists
        for wire in self.wires:
            if (wire.start == start_node and wire.end == end_node) or \
               (wire.start == end_node and wire.end == start_node):
                return False
        
        return True

    def draw_workspace(self):
        # Draw grid first
        self.draw_grid()
        
        # Draw tools section header
        font = pygame.font.SysFont('tahoma', 24, bold=True)
        text_surf = font.render("Tools", True, BLACK)
        screen.blit(text_surf, (20, 40))
        
        # Draw separator line
        pygame.draw.line(screen, GRAY, (10, 70), (270, 70), 2)
        
        # Draw components and wires
        workspace_rect = pygame.Rect(WORKSPACE_PADDING, 60, 
                                    self.settings['width']-2*WORKSPACE_PADDING, 
                                    self.settings['height']-160)
        
        pygame.draw.rect(screen, BLACK, workspace_rect, 2, border_radius=10)
        pygame.draw.rect(screen, WHITE, workspace_rect.inflate(-4, -4))
        
        for comp in self.components:
            comp.draw()
        
        for wire in self.wires:
            wire.draw()
        
        if self.current_tool == "wire" and self.wire_start:
            pygame.draw.line(screen, RED, self.wire_start, pygame.mouse.get_pos(), 3)
        
        # Draw zoom buttons
        for btn in self.zoom_buttons:
            btn.draw(pygame.mouse.get_pos())
        
        # Draw component context menus
        for comp in self.components:
            if comp.context_menu_active:
                comp.show_context_menu(screen, self.cell_size)

    def draw_menu(self):
        pygame.draw.rect(screen, LIGHT_BLUE, (0, 0, self.settings['width'], self.settings['height']))
        pygame.draw.rect(screen, WHITE, (self.settings['width']//2-200, self.settings['height']//2-150, 400, 300), border_radius=20)
        
        font = pygame.font.SysFont('tahoma', 40, bold=True)
        text_surf = font.render("Circuit Simulator", True, DARK_GRAY)
        screen.blit(text_surf, (self.settings['width']//2 - text_surf.get_width()//2, 100))
        
        for btn in self.menu_buttons:
            btn.draw(pygame.mouse.get_pos())

    def draw_settings(self):
        pygame.draw.rect(screen, LIGHT_BLUE, (0, 0, self.settings['width'], self.settings['height']))
        pygame.draw.rect(screen, WHITE, (self.settings['width']//2-250, self.settings['height']//2-150, 500, 300), border_radius=20)
        
        font = pygame.font.SysFont('tahoma', 30, bold=True)
        text_surf = font.render("Settings", True, DARK_GRAY)
        screen.blit(text_surf, (self.settings['width']//2 - text_surf.get_width()//2, self.settings['height']//2 - 120))
        
        for i, inp in enumerate(self.settings_inputs):
            label = ["Screen Width:", "Screen Height:"][i]
            font = pygame.font.SysFont('tahoma', 20)
            text_surf = font.render(label, True, DARK_GRAY)
            screen.blit(text_surf, (self.settings['width']//2 - 220, self.settings['height']//2 - 50 + i*60))
            
            inp.rect = pygame.Rect(self.settings['width']//2 - 100, self.settings['height']//2 - 50 + i*60, 200, 40)
            color = LIGHT_BLUE if inp.active else WHITE
            pygame.draw.rect(screen, color, inp.rect, border_radius=5)
            pygame.draw.rect(screen, DARK_GRAY, inp.rect, 2, border_radius=5)
            
            text_surf = font.render(inp.text, True, BLACK)
            screen.blit(text_surf, (inp.rect.x + 10, inp.rect.centery - 10))
        
        self.apply_btn.draw(pygame.mouse.get_pos())

    def draw(self):
        screen.fill(WHITE)
        
        if self.current_screen == "menu":
            self.draw_menu()
        elif self.current_screen == "settings":
            self.draw_settings()
        elif self.current_screen == "main":
            pygame.draw.rect(screen, LIGHT_BLUE, (0, 0, self.settings['width'], 60))
            pygame.draw.rect(screen, LIGHT_BLUE, (0, self.settings['height']-100, self.settings['width'], 100))
            
            sidebar_rect = pygame.Rect(0, 60, 200, self.settings['height']-160)
            pygame.draw.rect(screen, WHITE, sidebar_rect, border_radius=10)
            
            for btn in self.control_buttons + self.tool_buttons:
                btn.draw(pygame.mouse.get_pos())
            
            self.draw_workspace()
        
        # Draw tooltip
        if self.tooltip_text:
            font = pygame.font.SysFont('tahoma', 16)
            text_surf = font.render(self.tooltip_text, True, BLACK)
            screen.blit(text_surf, (mouse_pos[0] + 15, mouse_pos[1] + 15))
        
        pygame.display.flip()

    def show_tooltip(self, text):
        self.tooltip_text = text
        self.tooltip_timer = 60  # Show for 1 second at 60 FPS

    def update_tooltip(self):
        if self.tooltip_timer > 0:
            self.tooltip_timer -= 1
        else:
            self.tooltip_text = None

if __name__ == "__main__":
    simulator = CircuitSimulator()
    while True:
        simulator.handle_events()
        simulator.update_tooltip()
        simulator.draw()
        clock.tick(FPS)
