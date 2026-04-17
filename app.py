import rumps

WORK_SECONDS = 20 * 60
BREAK_SECONDS = 20


class EyeStrainTimer(rumps.App):
    def __init__(self):
        super().__init__("👁", quit_button=None)
        self.remaining = WORK_SECONDS
        self.on_break = False
        self.paused = False

        self.status_item = rumps.MenuItem("", callback=None)
        self.pause_item = rumps.MenuItem("Pause", callback=self.toggle_pause)
        self.menu = [
            self.status_item,
            None,
            self.pause_item,
            rumps.MenuItem("Reset", callback=self.reset),
            None,
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        self._update_display()
        rumps.Timer(self.tick, 1).start()

    def tick(self, _sender):
        if self.paused:
            return
        self.remaining -= 1
        if self.remaining <= 0:
            if self.on_break:
                self._end_break()
            else:
                self._start_break()
        else:
            self._update_display()

    def _start_break(self):
        self.on_break = True
        self.remaining = BREAK_SECONDS
        rumps.notification(
            "Eye Strain Timer",
            "Time for a break!",
            "Look 20 feet away for 20 seconds.",
            sound=True,
        )
        self._update_display()

    def _end_break(self):
        self.on_break = False
        self.remaining = WORK_SECONDS
        rumps.notification(
            "Eye Strain Timer",
            "Break over!",
            "Next break in 20 minutes.",
            sound=True,
        )
        self._update_display()

    def _update_display(self):
        if self.on_break:
            self.title = f"Break {self.remaining}s"
            self.status_item.title = f"Break: {self.remaining}s remaining"
        else:
            m, s = divmod(self.remaining, 60)
            self.title = f"{m:02d}:{s:02d}"
            self.status_item.title = f"Next break in {m:02d}:{s:02d}"

    def toggle_pause(self, sender):
        self.paused = not self.paused
        sender.title = "Resume" if self.paused else "Pause"
        if self.paused:
            self.title = "⏸"

    def reset(self, _sender):
        self.paused = False
        self.on_break = False
        self.remaining = WORK_SECONDS
        self.pause_item.title = "Pause"
        self._update_display()


if __name__ == "__main__":
    EyeStrainTimer().run()
