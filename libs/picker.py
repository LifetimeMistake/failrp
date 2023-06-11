import curses
import time

def pick_from_list(lst, default=0, timeout=None, msg=""):
    interrupted = False
    if default >= len(lst):
        raise IndexError("Default Index out of range")
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    h, w = 0,0
    # Set up non-blocking input mode
    stdscr.nodelay(1)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    try:
        result = lst[default]
        selected = 0
        start_time = time.monotonic()

        stdscr.clear()
        while True:
            if h != stdscr.getmaxyx()[0] or w != stdscr.getmaxyx()[1]:
                stdscr.clear()
            h, w = stdscr.getmaxyx()
            for i, item in enumerate(lst):
                if i == selected:
                    stdscr.addstr(i+ h//2, w//2-len(f"> {item}  ")//2, f"> {item}  ", curses.color_pair(1))
                else:
                    stdscr.addstr(i+ h//2, w//2-len(f"  {item}  ")//2, f"  {item}  ")
            timing = f"(Default: {lst[default]}) Default will be picked in {int(5 - (time.monotonic() - start_time))} seconds" if not interrupted else f"{' '*20}You Picked {lst[selected]}{' '*20}"
            stdscr.addstr(len(lst) + 1 + h//2, w//2-len(timing)//2, timing)
            stdscr.addstr(0, w//2-len(msg)//2-1, msg)

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

class AnsiPicker:
    def __init__(self, options: "dict[str, any]"):
        self.options = options
    def ask(self, timeout=10, default_key = None, msg=""):
        if not default_key:
            idx = 0
        else:
            idx = list(self.options.keys()).index(default_key)
        out = pick_from_list(list(self.options.keys()), idx, timeout, msg=msg)
        return self.options[out]
