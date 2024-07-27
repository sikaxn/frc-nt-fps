import pygame
import ntcore
import sys

# Initialize pygame
pygame.init()

# Create a display surface
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption('Keyboard and Mouse Events')

# Initialize NetworkTables
inst = ntcore.NetworkTableInstance.getDefault()
inst.startClient4("KeyboardMouseClient")
inst.setServer("127.0.0.1") #Change this to your roboRIO ip address (10.TE.AM.2)
table = inst.getTable("KeyboardMouseEvents")

# Create and publish boolean topics for keyboard and mouse buttons
key_names = "qwertasdfghzxcv12345".upper()
mod_keys = ["ctrl", "alt", "shift"]
mouse_buttons = ["mouse_left", "mouse_right", "mouse_middle"]

key_topics = {key.lower(): table.getBooleanTopic(f"key_{key.lower()}").publish() for key in key_names}
mod_topics = {mod: table.getBooleanTopic(f"key_{mod}").publish() for mod in mod_keys}
mouse_topics = {btn: table.getBooleanTopic(f"btn_{btn}").publish() for btn in mouse_buttons}

# Create and publish double topics for mouse speed
mouse_speed_x_topic = table.getDoubleTopic("mouse_speed_x").publish()
mouse_speed_y_topic = table.getDoubleTopic("mouse_speed_y").publish()
scroll_wheel_speed_topic = table.getDoubleTopic("scroll_wheel_speed").publish()

# Define maximum speeds for normalization
MAX_MOUSE_SPEED = 1000  # Adjust as necessary
MAX_SCROLL_SPEED = 10   # Adjust as necessary

# Helper function to update NetworkTables and flush
def update_entry(entry, value):
    entry.set(value)
    inst.flush()

def draw_text(surface, text, position, font, color=(255, 255, 255)):
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, position)

def reset_states(key_status, mod_status, mouse_status, mouse_speed_x_topic, mouse_speed_y_topic, scroll_wheel_speed_topic):
    for key in key_status:
        key_status[key] = False
        update_entry(key_topics[key.lower()], False)
    for mod in mod_status:
        mod_status[mod] = False
        update_entry(mod_topics[mod], False)
    for btn in mouse_status:
        mouse_status[btn] = False
        update_entry(mouse_topics[btn], False)
    update_entry(mouse_speed_x_topic, 0)
    update_entry(mouse_speed_y_topic, 0)
    update_entry(scroll_wheel_speed_topic, 0)

def normalize_speed(speed, max_speed):
    return max(-1, min(1, speed / max_speed))

def main():
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    last_mouse_pos = pygame.mouse.get_pos()
    last_time = pygame.time.get_ticks()
    last_update_time = last_time

    key_status = {key: False for key in key_names}
    mod_status = {mod: False for mod in mod_keys}
    mouse_status = {btn: False for btn in mouse_buttons}

    capture_enabled = True
    mouse_speed_x = 0
    mouse_speed_y = 0
    scroll_wheel_speed = 0

    # Lock mouse in the window and hide the cursor
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)

    running = True
    while running:
        try:
            screen.fill((0, 0, 0))  # Clear screen with black color

            try:
                events = pygame.event.get()
            except Exception as e:
                print(f"Error getting events: {e}")
                events = []

            for event in events:
                try:
                    if event.type == pygame.QUIT:
                        running = False

                    elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                        key_name = pygame.key.name(event.key).upper()
                        if key_name == 'P' and event.type == pygame.KEYDOWN:
                            capture_enabled = not capture_enabled
                            if capture_enabled:
                                pygame.event.set_grab(True)
                                pygame.mouse.set_visible(False)
                                print("Capture resumed.")
                            else:
                                reset_states(key_status, mod_status, mouse_status, mouse_speed_x_topic, mouse_speed_y_topic, scroll_wheel_speed_topic)
                                pygame.event.set_grab(False)
                                pygame.mouse.set_visible(True)
                                print("Capture paused.")
                        if capture_enabled:
                            if key_name.lower() in key_topics:
                                update_entry(key_topics[key_name.lower()], event.type == pygame.KEYDOWN)
                                key_status[key_name] = (event.type == pygame.KEYDOWN)
                            elif key_name in mod_topics:
                                update_entry(mod_topics[key_name], event.type == pygame.KEYDOWN)
                                mod_status[key_name] = (event.type == pygame.KEYDOWN)

                    elif capture_enabled:
                        if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP:
                            button = None
                            if event.button == 1:
                                button = "mouse_left"
                            elif event.button == 2:
                                button = "mouse_middle"
                            elif event.button == 3:
                                button = "mouse_right"
                            if button:
                                update_entry(mouse_topics[button], event.type == pygame.MOUSEBUTTONDOWN)
                                mouse_status[button] = (event.type == pygame.MOUSEBUTTONDOWN)

                        elif event.type == pygame.MOUSEMOTION:
                            mouse_x, mouse_y = pygame.mouse.get_pos()
                            current_time = pygame.time.get_ticks()
                            time_elapsed = current_time - last_time
                            if time_elapsed > 0:
                                dx = mouse_x - last_mouse_pos[0]
                                dy = mouse_y - last_mouse_pos[1]
                                mouse_speed_x = normalize_speed(dx / time_elapsed * 1000, MAX_MOUSE_SPEED)
                                mouse_speed_y = normalize_speed(dy / time_elapsed * 1000, MAX_MOUSE_SPEED)
                                update_entry(mouse_speed_x_topic, mouse_speed_x)
                                update_entry(mouse_speed_y_topic, mouse_speed_y)
                                last_update_time = current_time
                            last_mouse_pos = (mouse_x, mouse_y)
                            last_time = current_time

                        elif event.type == pygame.MOUSEWHEEL:
                            current_time = pygame.time.get_ticks()
                            time_elapsed = current_time - last_time
                            if time_elapsed > 0:
                                scroll_wheel_speed = normalize_speed(event.y / time_elapsed * 1000, MAX_SCROLL_SPEED)
                                update_entry(scroll_wheel_speed_topic, scroll_wheel_speed)
                                last_update_time = current_time

                except Exception as e:
                    print(f"Error processing event: {e}")

            # Check for idle time and reset speeds if necessary
            current_time = pygame.time.get_ticks()
            if current_time - last_update_time > 100:
                mouse_speed_x = 0
                mouse_speed_y = 0
                scroll_wheel_speed = 0
                update_entry(mouse_speed_x_topic, 0)
                update_entry(mouse_speed_y_topic, 0)
                update_entry(scroll_wheel_speed_topic, 0)

            # Draw key statuses
            y_offset = 20
            for key, status in key_status.items():
                draw_text(screen, f"{key}: {'Pressed' if status else 'Released'}", (20, y_offset), font)
                y_offset += 20

            # Draw modifier key statuses
            for mod, status in mod_status.items():
                draw_text(screen, f"{mod}: {'Pressed' if status else 'Released'}", (20, y_offset), font)
                y_offset += 20

            # Draw mouse button statuses
            for btn, status in mouse_status.items():
                draw_text(screen, f"{btn}: {'Pressed' if status else 'Released'}", (20, y_offset), font)
                y_offset += 20

            # Draw mouse speeds
            draw_text(screen, f"Mouse Speed X: {mouse_speed_x:.2f}", (20, y_offset), font)
            y_offset += 20
            draw_text(screen, f"Mouse Speed Y: {mouse_speed_y:.2f}", (20, y_offset), font)
            y_offset += 20
            draw_text(screen, f"Scroll Wheel Speed: {scroll_wheel_speed:.2f}", (20, y_offset), font)
            y_offset += 20

            if not capture_enabled:
                draw_text(screen, "Capture Paused. Press 'P' to Resume.", (20, y_offset), font, (255, 0, 0))

            pygame.display.flip()
            clock.tick(60)  # Cap the frame rate at 60 FPS

        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            running = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
