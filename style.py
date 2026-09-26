import tkinter as tk
from tkinter import ttk


# colours ---------------------------------------------

BG = "#FAF7FF"
CARD = "#FFFFFF"

LAVENDER = "#D9C5F3"
LAVENDER_LIGHT = "#F4EEFB"
LAVENDER_DARK = "#7653B5"

PINK = "#F6D7E8"
PINK_DARK = "#C46F9D"

GREEN = "#DDF0E2"
GREEN_DARK = "#659776"

LOW_COLOUR = "#FBE6F0"
EXPIRED_COLOUR = "#EFE5EC"
USED_COLOUR = "#F1EDF3"

TEXT = "#4F4658"
MUTED = "#8D8495"
BORDER = "#E8DEF1"

GRAPH_BG = "#FDFBFF"
GRAPH_TRACK = "#EFE8F7"
GRAPH_BAR = "#BFA5E5"
GRAPH_BAR_DARK = "#8B63C6"

SHADOW = "#EEE7F4"
WHITE = "#FFFFFF"


# ttk styles ---------------------------------------------

def setup_styles():
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "Treeview",
        background=CARD,
        foreground=TEXT,
        rowheight=42,
        fieldbackground=CARD,
        font=("Arial", 10),
        borderwidth=0
    )

    style.configure(
        "Treeview.Heading",
        background="#EADDF8",
        foreground=LAVENDER_DARK,
        font=("Arial", 10, "bold"),
        padding=11,
        borderwidth=0
    )

    style.map(
        "Treeview",
        background=[
            ("selected", "#EFE5FA")
        ],
        foreground=[
            ("selected", TEXT)
        ]
    )

    style.configure(
        "TScrollbar",
        background=LAVENDER_LIGHT,
        troughcolor=BG,
        borderwidth=0,
        arrowcolor=LAVENDER_DARK
    )


# rounded rectangle helper ---------------------------------------------

def create_rounded_rectangle(
    canvas,
    x1,
    y1,
    x2,
    y2,
    radius=18,
    **kwargs
):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1
    ]

    return canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=24,
        **kwargs
    )


# rounded panel ---------------------------------------------

class RoundedPanel(tk.Canvas):

    def __init__(
        self,
        parent,
        bg=CARD,
        parent_bg=BG,
        border=BORDER,
        radius=18,
        padding=14,
        height=120
    ):
        super().__init__(
            parent,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
            height=height
        )

        self.panel_bg = bg
        self.border = border
        self.radius = radius
        self.padding = padding

        self.body = tk.Frame(
            self,
            bg=bg
        )

        self.body_window = self.create_window(
            padding,
            padding,
            anchor="nw",
            window=self.body
        )

        self.bind(
            "<Configure>",
            self._redraw
        )

        self.body.bind(
            "<Configure>",
            self._resize_to_body
        )


    def _redraw(
        self,
        event=None
    ):
        width = max(
            self.winfo_width(),
            50
        )

        height = max(
            self.winfo_height(),
            50
        )

        self.delete(
            "panel_shape"
        )

        create_rounded_rectangle(
            self,
            1,
            1,
            width - 1,
            height - 1,
            self.radius,
            fill=self.panel_bg,
            outline=self.border,
            width=1,
            tags="panel_shape"
        )

        self.tag_lower(
            "panel_shape"
        )

        self.coords(
            self.body_window,
            self.padding,
            self.padding
        )

        self.itemconfigure(
            self.body_window,
            width=max(
                1,
                width -
                self.padding * 2
            )
        )


    def _resize_to_body(
        self,
        event=None
    ):
        wanted = max(
            70,
            self.body.winfo_reqheight() +
            self.padding * 2
        )

        current = int(
            float(
                self.cget(
                    "height"
                )
            )
        )

        if abs(
            wanted -
            current
        ) > 2:
            self.configure(
                height=wanted
            )

        self.after_idle(
            self._redraw
        )


# rounded button ---------------------------------------------

class RoundedButton(tk.Canvas):

    def __init__(
        self,
        parent,
        text,
        command=None,
        width=180,
        height=44,
        radius=16,
        bg=LAVENDER,
        fg=TEXT,
        hover_bg=None,
        selected_bg=None,
        selected_fg=None,
        font=("Arial", 10, "bold")
    ):
        parent_bg = parent.cget("bg")

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2"
        )

        self.command = command
        self.normal_bg = bg
        self.hover_bg = (
            hover_bg
            or "#EADDF8"
        )

        self.selected_bg = (
            selected_bg
            or LAVENDER
        )

        self.normal_fg = fg
        self.selected_fg = (
            selected_fg
            or LAVENDER_DARK
        )

        self.radius = radius
        self.is_selected = False
        self.label = text
        self.font_value = font

        self.bind(
            "<Button-1>",
            self._click
        )

        self.bind(
            "<Enter>",
            self._enter
        )

        self.bind(
            "<Leave>",
            self._leave
        )

        self._draw(
            self.normal_bg,
            self.normal_fg
        )


    def _draw(
        self,
        background,
        foreground
    ):
        self.delete(
            "all"
        )

        width = int(
            self["width"]
        )

        height = int(
            self["height"]
        )

        create_rounded_rectangle(
            self,
            1,
            1,
            width - 1,
            height - 1,
            self.radius,
            fill=background,
            outline="",
        )

        self.create_text(
            width / 2,
            height / 2,
            text=self.label,
            fill=foreground,
            font=self.font_value
        )


    def set_selected(
        self,
        selected
    ):
        self.is_selected = selected

        if selected:
            self._draw(
                self.selected_bg,
                self.selected_fg
            )

        else:
            self._draw(
                self.normal_bg,
                self.normal_fg
            )


    def _click(
        self,
        event=None
    ):
        if self.command:
            self.command()


    def _enter(
        self,
        event=None
    ):
        if not self.is_selected:
            self._draw(
                self.hover_bg,
                self.normal_fg
            )


    def _leave(
        self,
        event=None
    ):
        self.set_selected(
            self.is_selected
        )
