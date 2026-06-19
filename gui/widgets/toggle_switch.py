"""iOS 風トグルスイッチウィジェット。"""
import tkinter as tk

from gui.theme import C_ON, C_OFF


class ToggleSwitch(tk.Canvas):
    W, H = 46, 26

    def __init__(self, parent, value: bool = True, on_change=None, **kw):
        kw.setdefault("bg", "white")
        super().__init__(parent, width=self.W, height=self.H,
                         highlightthickness=0, bd=0, **kw)
        self._value = value
        self.on_change = on_change
        self.bind("<Button-1>", self._click)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.W, self.H
        r = h // 2
        color = C_ON if self._value else C_OFF
        self.create_arc(1, 1, 1 + h - 2, h - 1, start=90, extent=180,
                        fill=color, outline=color)
        self.create_arc(w - h + 1, 1, w - 1, h - 1, start=270, extent=180,
                        fill=color, outline=color)
        self.create_rectangle(r, 1, w - r, h - 1, fill=color, outline=color)
        pad = 3
        cx = (w - r - pad) if self._value else (r + pad)
        self.create_oval(cx - r + pad + 1, pad,
                         cx + r - pad - 1, h - pad,
                         fill="white", outline="white")

    def _click(self, _=None):
        self._value = not self._value
        self._draw()
        if self.on_change:
            self.on_change(self._value)

    def get(self) -> bool:
        return self._value

    def set(self, value: bool):
        if self._value != value:
            self._value = value
            self._draw()
