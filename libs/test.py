import curses
import time

def pick_from_list(lst, default=0, timeout=None):
    interrupted = False
    if default >= len(lst):
        raise IndexError("Default Index out of range")
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    # Set up non-blocking input mode
    stdscr.nodelay(1)

    try:
        result = lst[default]
        selected = 0
        start_time = time.monotonic()

        stdscr.clear()
        while True:
            for i, item in enumerate(lst):
                if i == selected:
                    stdscr.addstr(i, 0, f"> {item}")
                else:
                    stdscr.addstr(i, 0, f"  {item}")
            timing = f"(Default: {lst[default]})\nDefault will be picked in {int(5 - (time.monotonic() - start_time))} seconds" if not interrupted else f"You Picked Option {lst[selected]}\n\n"
            stdscr.addstr(len(lst) + 1, 0, f"\n"+timing)
            # Check if timeout has elapsed
            if timeout is not None and time.monotonic() - start_time >= timeout and not interrupted:
                result = lst[default]
                break

            stdscr.refresh()

            key = stdscr.getch()

            if key == ord('\n'):
                result = lst[selected]
                break
            elif key == curses.KEY_UP:
                interrupted = True
                selected = (selected - 1) % len(lst)
                result = lst[selected]
            elif key == curses.KEY_DOWN:
                interrupted = True
                selected = (selected + 1) % len(lst)
                result = lst[selected]

            time.sleep(0.03)

        return result
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()

options = ["Option 1", "Option 2", "Option 3", "Option 4", "Option 5"]
default = 4
timeout = 5

print("Use arrow keys to navigate, Enter to confirm. Press Ctrl-C to exit.")

result = pick_from_list(options, default=default, timeout=timeout)

print(f"\nYou picked: {result}")