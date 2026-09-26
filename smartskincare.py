from datetime import datetime, date, timedelta
from tkinter import ttk, messagebox
import tkinter as tk
import random

from cosmos_db import (
    connect_cosmos,
    add_product,
    get_products,
    update_product_weight,
    update_product_status,
    mark_replacement_created,
    replacement_exists_for,
    disconnect_cosmos
)

from azure_connection import (
    connect_azure,
    send_inventory_update,
    disconnect_azure
)

from style import (
    setup_styles,
    create_rounded_rectangle,
    RoundedPanel,
    RoundedButton,
    BG,
    CARD,
    LAVENDER,
    LAVENDER_LIGHT,
    LAVENDER_DARK,
    PINK,
    PINK_DARK,
    GREEN,
    GREEN_DARK,
    LOW_COLOUR,
    EXPIRED_COLOUR,
    USED_COLOUR,
    TEXT,
    MUTED,
    BORDER,
    GRAPH_BG,
    GRAPH_BAR_DARK
)


APP_BUILD = "2026-08-28-compact-summary-v4"

# constants ---------------------------------------------

UPDATE_INTERVAL_MS = 10000
LOW_STOCK_THRESHOLD = 30
MAX_DECREASE_PERCENT = 10


# product calculations ---------------------------------------------

def get_remaining_percentage(initial_weight, current_weight):
    try:
        initial_weight = float(initial_weight or 0)
        current_weight = float(current_weight or 0)
    except (ValueError, TypeError):
        return 0.0

    if initial_weight <= 0:
        return 0.0

    percentage = (
        current_weight /
        initial_weight
    ) * 100

    return round(
        max(0.0, min(100.0, percentage)),
        1
    )


def get_usage_percentage(initial_weight, current_weight):
    return round(
        100 - get_remaining_percentage(
            initial_weight,
            current_weight
        ),
        1
    )


# expiry ---------------------------------------------

def parse_expiry(expiry_date):
    try:
        return datetime.strptime(
            str(expiry_date),
            "%Y-%m-%d"
        ).date()
    except (ValueError, TypeError):
        return None


def is_expired(expiry_date):
    expiry = parse_expiry(expiry_date)

    if expiry is None:
        return False

    return expiry < date.today()


def days_until_expiry(expiry_date):
    expiry = parse_expiry(expiry_date)

    if expiry is None:
        return 999999

    return (
        expiry - date.today()
    ).days


# status ---------------------------------------------

def get_product_status(remaining, expiry_date):
    # used has priority only when the item is completely empty
    if remaining <= 0:
        return "used"

    # expired has priority over low and in use while stock remains
    if is_expired(expiry_date):
        return "expired"

    if remaining >= 100:
        return "new"

    if remaining < LOW_STOCK_THRESHOLD:
        return "low"

    return "in use"


def get_stock_status(status):
    if status == "new":
        return "full"

    if status == "in use":
        return "in stock"

    if status == "low":
        return "low"

    if status == "used":
        return "empty"

    return "expired"


# product identity ---------------------------------------------

def product_group_key(product):
    # barcode is the product identity
    return str(
        product.get("barcode", "")
    ).strip()


def batch_exists(batch_code):
    wanted = str(batch_code).strip().lower()

    return any(
        str(product.get("batch_code", "")).strip().lower() == wanted
        for product in get_products()
    )


# random replacement values ---------------------------------------------

def generate_batch_code():
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for _ in range(100):
        batch = (
            f"{random.choice(letters)}"
            f"{random.choice(letters)}-"
            f"{random.randint(1000, 9999)}"
        )

        if not batch_exists(batch):
            return batch

    return (
        f"BT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    )


def generate_expiry_date():
    # replacements are always future stock
    days = random.randint(180, 720)

    return (
        date.today() + timedelta(days=days)
    ).strftime("%Y-%m-%d")


# create replacement ---------------------------------------------

def create_replacement_product(product):
    source_id = product.get("id")

    # prevent duplicate replacements for the same finished item
    if replacement_exists_for(source_id):
        mark_replacement_created(source_id)
        return None

    initial_weight = float(
        product.get("initial_weight", 0) or 0
    )

    replacement = add_product(
        barcode=product.get("barcode", ""),
        brand=product.get("brand", ""),
        name=product.get("name", ""),
        category=product.get("category", ""),
        batch_code=generate_batch_code(),
        expiry_date=generate_expiry_date(),
        initial_weight=initial_weight,
        current_weight=initial_weight,
        status="new",
        product_type="normal",
        replacement_created=0,
        replacement_source_id=source_id
    )

    # mark only after the replacement is successfully created
    mark_replacement_created(source_id)

    return replacement


# update statuses ---------------------------------------------

def update_all_statuses():
    products = get_products()

    for product in products:
        if product.get("product_type", "normal") == "unused":
            if product.get("status") != "unused":
                update_product_status(
                    product["id"],
                    "unused"
                )
            continue

        remaining = get_remaining_percentage(
            product.get("initial_weight"),
            product.get("current_weight")
        )

        correct_status = get_product_status(
            remaining,
            product.get("expiry_date")
        )

        if product.get("status") != correct_status:
            update_product_status(
                product["id"],
                correct_status
            )


# automatic replacement ---------------------------------------------

def check_for_replacements():
    products = get_products()

    for product in products:
        if product.get("product_type", "normal") == "unused":
            continue

        remaining = get_remaining_percentage(
            product.get("initial_weight"),
            product.get("current_weight")
        )

        status = get_product_status(
            remaining,
            product.get("expiry_date")
        )

        if status not in (
            "used",
            "expired"
        ):
            continue

        if int(
            product.get(
                "replacement_created",
                0
            ) or 0
        ) == 1:
            continue

        update_product_status(
            product["id"],
            status
        )

        create_replacement_product(
            product
        )


# automatic usage ---------------------------------------------

def select_product_for_use(group):
    already_open = []
    unopened = []

    for product in group:
        if product.get("product_type", "normal") == "unused":
            continue

        remaining = get_remaining_percentage(
            product.get("initial_weight"),
            product.get("current_weight")
        )

        if remaining <= 0:
            continue

        if is_expired(
            product.get("expiry_date")
        ):
            continue

        if remaining < 100:
            already_open.append(product)
        else:
            unopened.append(product)

    # if a unit is already in use, always finish it first
    if already_open:
        already_open.sort(
            key=lambda product: (
                days_until_expiry(
                    product.get("expiry_date")
                ),
                str(
                    product.get("batch_code", "")
                ).lower()
            )
        )
        return already_open[0]

    # otherwise start the unopened unit closest to expiry
    if unopened:
        unopened.sort(
            key=lambda product: (
                days_until_expiry(
                    product.get("expiry_date")
                ),
                str(
                    product.get("batch_code", "")
                ).lower()
            )
        )
        return unopened[0]

    return None


def simulate_product_usage():
    products = get_products()
    groups = {}

    for product in products:
        barcode = product_group_key(product)

        if not barcode:
            continue

        groups.setdefault(
            barcode,
            []
        ).append(product)

    candidates = []

    for barcode, group in groups.items():
        selected = select_product_for_use(group)

        if selected is not None:
            candidates.append(selected)

    if not candidates:
        return None

    # only one product unit is changed during each 10-second update
    selected = random.choice(candidates)

    initial_weight = float(
        selected.get("initial_weight", 0) or 0
    )

    current_weight = float(
        selected.get("current_weight", 0) or 0
    )

    if initial_weight <= 0 or current_weight <= 0:
        return None

    # decrease is always between 0 and 10 percent of the original unit
    decrease_percentage = random.uniform(
        0.0,
        MAX_DECREASE_PERCENT
    )

    decrease_weight = (
        initial_weight *
        decrease_percentage /
        100
    )

    new_weight = max(
        0.0,
        current_weight - decrease_weight
    )

    update_product_weight(
        selected["id"],
        round(new_weight, 3)
    )

    return selected["id"]


# iot telemetry ---------------------------------------------

def send_inventory_telemetry():
    products = get_products()

    for product in products:
        remaining = get_remaining_percentage(
            product.get("initial_weight"),
            product.get("current_weight")
        )

        if product.get("product_type", "normal") == "unused":
            status = "unused"
        else:
            status = get_product_status(
                remaining,
                product.get("expiry_date")
            )

        payload = dict(product)
        payload["remaining"] = remaining
        payload["status"] = status
        payload["stock_status"] = (
            "unused"
            if status == "unused"
            else get_stock_status(status)
        )

        send_inventory_update(payload)


# application ---------------------------------------------

class BeautyClinicApp:

    def __init__(self, root):
        self.root = root
        self.root.title(
            "♡ beauty clinic inventory"
        )
        self.root.geometry(
            "1440x900"
        )
        self.root.minsize(
            1080,
            700
        )
        self.root.configure(
            bg=BG
        )

        setup_styles()

        self.selected_barcode = None

        self.create_pages()
        self.create_scrollable_dashboard()
        self.create_header()
        self.create_summary()
        self.create_inventory_table()
        self.create_graph_section()
        self.create_unused_table()
        self.create_history_table()

        self.run_inventory_cycle(
            simulate=False
        )

        self.root.after(
            UPDATE_INTERVAL_MS,
            self.automatic_update
        )


    # pages ---------------------------------------------

    def create_pages(self):
        self.nav_shell = tk.Frame(
            self.root,
            bg=BG,
            padx=24,
            pady=12
        )

        self.nav_shell.pack(
            fill="x"
        )

        self.nav_bar = tk.Frame(
            self.nav_shell,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=8,
            pady=8
        )

        self.nav_bar.pack(
            fill="x"
        )

        self.main_nav_button = RoundedButton(
            self.nav_bar,
            text="♡  MAIN INVENTORY",
            command=lambda: self.show_page(
                "main"
            ),
            width=235,
            height=46,
            bg="#F8F4FC",
            hover_bg="#EFE5FA",
            selected_bg="#E2D1F5",
            selected_fg=LAVENDER_DARK
        )

        self.main_nav_button.pack(
            side="left",
            padx=5
        )

        self.unused_nav_button = RoundedButton(
            self.nav_bar,
            text="♡  UNUSED PRODUCTS",
            command=lambda: self.show_page(
                "unused"
            ),
            width=245,
            height=46,
            bg="#F8F4FC",
            hover_bg="#F3E7F2",
            selected_bg="#F2DDEC",
            selected_fg=PINK_DARK
        )

        self.unused_nav_button.pack(
            side="left",
            padx=5
        )

        self.history_nav_button = RoundedButton(
            self.nav_bar,
            text="⌛  HISTORY",
            command=lambda: self.show_page(
                "history"
            ),
            width=185,
            height=46,
            bg="#F8F4FC",
            hover_bg="#EFE8F4",
            selected_bg="#E9DFF1",
            selected_fg=LAVENDER_DARK
        )

        self.history_nav_button.pack(
            side="left",
            padx=5
        )

        self.page_container = tk.Frame(
            self.root,
            bg=BG
        )

        self.page_container.pack(
            fill="both",
            expand=True
        )

        self.main_page = tk.Frame(
            self.page_container,
            bg=BG
        )

        self.unused_page = tk.Frame(
            self.page_container,
            bg=BG
        )

        self.history_page = tk.Frame(
            self.page_container,
            bg=BG
        )

        self.pages = {
            "main": self.main_page,
            "unused": self.unused_page,
            "history": self.history_page
        }

        self.show_page(
            "main"
        )


    def show_page(
        self,
        page_name
    ):
        buttons = {
            "main": self.main_nav_button,
            "unused": self.unused_nav_button,
            "history": self.history_nav_button
        }

        for page in self.pages.values():
            page.pack_forget()

        target = self.pages.get(
            page_name,
            self.main_page
        )

        target.pack(
            fill="both",
            expand=True
        )

        for name, button in buttons.items():
            button.set_selected(
                name == page_name
            )


    # scrolling ---------------------------------------------

    def create_scrollable_dashboard(self):
        self.main_canvas = tk.Canvas(
            self.main_page,
            bg=BG,
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            self.main_page,
            orient="vertical",
            command=self.main_canvas.yview
        )

        self.main_canvas.configure(
            yscrollcommand=scrollbar.set
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.main_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.dashboard_frame = tk.Frame(
            self.main_canvas,
            bg=BG
        )

        self.dashboard_window = self.main_canvas.create_window(
            (0, 0),
            window=self.dashboard_frame,
            anchor="nw"
        )

        self.dashboard_frame.bind(
            "<Configure>",
            self.update_scrollregion
        )

        self.main_canvas.bind(
            "<Configure>",
            self.resize_dashboard
        )

        self.root.bind_all(
            "<MouseWheel>",
            self.mousewheel
        )


    def update_scrollregion(self, event=None):
        self.main_canvas.configure(
            scrollregion=self.main_canvas.bbox("all")
        )


    def resize_dashboard(self, event):
        self.main_canvas.itemconfigure(
            self.dashboard_window,
            width=event.width
        )


    def mousewheel(self, event):
        if event.delta:
            self.main_canvas.yview_scroll(
                int(-1 * event.delta / 120),
                "units"
            )


    # header ---------------------------------------------

    def create_header(self):
        header_outer = tk.Frame(
            self.dashboard_frame,
            bg=BG,
            padx=28,
            pady=12
        )
        header_outer.pack(
            fill="x"
        )

        header_card = RoundedPanel(
            header_outer,
            bg=CARD,
            parent_bg=BG,
            border=BORDER,
            radius=22,
            padding=18
        )
        header_card.pack(
            fill="x"
        )

        header = header_card.body

        top = tk.Frame(
            header,
            bg=CARD
        )
        top.pack(
            fill="x"
        )

        title_group = tk.Frame(
            top,
            bg=CARD
        )
        title_group.pack(
            side="left"
        )

        tk.Label(
            title_group,
            text="♡  Beauty Clinic Inventory",
            bg=CARD,
            fg=LAVENDER_DARK,
            font=(
                "Arial",
                24,
                "bold"
            )
        ).pack(
            anchor="w"
        )

        tk.Label(
            title_group,
            text=(
                "smart skincare stock tracking"
                "  •  barcode grouped"
                "  •  automatic lifecycle monitoring"
            ),
            bg=CARD,
            fg=MUTED,
            font=(
                "Arial",
                9
            )
        ).pack(
            anchor="w",
            pady=5
        )

        controls = tk.Frame(
            top,
            bg=CARD
        )
        controls.pack(
            side="right"
        )

        add_product_button = RoundedButton(
            controls,
            text="＋  ADD PRODUCT",
            command=self.open_add_window,
            width=185,
            height=44,
            bg=LAVENDER,
            hover_bg="#CDB3EC",
            selected_bg=LAVENDER,
            selected_fg=TEXT
        )
        add_product_button.pack(
            side="left",
            padx=5
        )

        add_unused_button = RoundedButton(
            controls,
            text="＋  ADD UNUSED PRODUCT",
            command=self.open_add_unused_window,
            width=225,
            height=44,
            bg=PINK,
            hover_bg="#F0C9DE",
            selected_bg=PINK,
            selected_fg=TEXT
        )
        add_unused_button.pack(
            side="left",
            padx=5
        )

        status_row = tk.Frame(
            header,
            bg=CARD
        )
        status_row.pack(
            fill="x",
            pady=12
        )

        self.notification_label = tk.Label(
            status_row,
            text="♡ inventory monitoring active",
            bg="#F7F0FD",
            fg=LAVENDER_DARK,
            font=(
                "Arial",
                10,
                "bold"
            ),
            padx=16,
            pady=8
        )
        self.notification_label.pack(
            side="left"
        )

        tk.Label(
            status_row,
            text="●  auto sync every 10s",
            bg=CARD,
            fg=GREEN_DARK,
            font=(
                "Arial",
                9,
                "bold"
            )
        ).pack(
            side="right",
            padx=8
        )

        self.unused_notice_card = RoundedPanel(
            header,
            bg="#FFF5FB",
            parent_bg=CARD,
            border="#F0D6E5",
            radius=16,
            padding=10
        )

        self.unused_notice_label = tk.Label(
            self.unused_notice_card.body,
            text="",
            bg="#FFF5FB",
            fg=PINK_DARK,
            justify="left",
            anchor="w",
            font=(
                "Arial",
                9,
                "bold"
            ),
            wraplength=1120
        )
        self.unused_notice_label.pack(
            fill="x"
        )


    # summary ---------------------------------------------

    def create_summary(self):
        summary_outer = tk.Frame(
            self.dashboard_frame,
            bg=BG
        )

        summary_outer.pack(
            fill="x",
            padx=28,
            pady=10
        )

        self.summary_frame = tk.Frame(
            summary_outer,
            bg=BG
        )

        self.summary_frame.pack(
            anchor="w"
        )

        self.total_label = self.create_summary_card(
            "♡",
            "active",
            PINK
        )

        self.in_use_label = self.create_summary_card(
            "✦",
            "in use",
            LAVENDER
        )

        self.low_label = self.create_summary_card(
            "!",
            "low stock",
            LOW_COLOUR
        )

        self.new_label = self.create_summary_card(
            "＋",
            "new",
            GREEN
        )

        self.history_label = self.create_summary_card(
            "⌛",
            "history",
            EXPIRED_COLOUR
        )


    def create_summary_card(
        self,
        icon,
        title,
        colour
    ):
        card_holder = tk.Frame(
            self.summary_frame,
            bg=BG,
            width=215,
            height=100
        )

        card_holder.pack(
            side="left",
            padx=6
        )

        card_holder.pack_propagate(
            False
        )

        panel = RoundedPanel(
            card_holder,
            bg=CARD,
            parent_bg=BG,
            border=BORDER,
            radius=18,
            padding=12,
            height=96
        )

        panel.pack(
            fill="both",
            expand=True
        )

        card = panel.body

        icon_box = tk.Label(
            card,
            text=icon,
            bg=colour,
            fg=TEXT,
            width=3,
            font=(
                "Arial",
                14,
                "bold"
            ),
            padx=5,
            pady=8
        )

        icon_box.pack(
            side="left",
            padx=(
                4,
                10
            )
        )

        text_box = tk.Frame(
            card,
            bg=CARD
        )

        text_box.pack(
            side="left",
            fill="y"
        )

        tk.Label(
            text_box,
            text=title.upper(),
            bg=CARD,
            fg=MUTED,
            font=(
                "Arial",
                8,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(
                5,
                1
            )
        )

        value_label = tk.Label(
            text_box,
            text="0",
            bg=CARD,
            fg=LAVENDER_DARK,
            font=(
                "Arial",
                17,
                "bold"
            )
        )

        value_label.pack(
            anchor="w"
        )

        return value_label


    # inventory table ---------------------------------------------

    def create_inventory_table(self):
        outer = tk.Frame(
            self.dashboard_frame,
            bg=BG,
            padx=28,
            pady=12
        )
        outer.pack(fill="x")

        tk.Label(
            outer,
            text="♡ active clinic inventory",
            bg=BG,
            fg=LAVENDER_DARK,
            font=("Arial", 13, "bold")
        ).pack(
            anchor="w",
            pady=7
        )

        card_panel = RoundedPanel(
            outer,
            bg=CARD,
            parent_bg=BG,
            border=BORDER,
            radius=20,
            padding=10
        )
        card_panel.pack(
            fill="x"
        )
        card = card_panel.body

        columns = (
            "brand",
            "product",
            "category",
            "barcode",
            "batch",
            "remaining",
            "stock",
            "expiry",
            "status"
        )

        self.tree = ttk.Treeview(
            card,
            columns=columns,
            show="headings",
            height=8
        )

        headings = {
            "brand": "brand",
            "product": "product",
            "category": "category",
            "barcode": "barcode",
            "batch": "batch code",
            "remaining": "remaining",
            "stock": "stock",
            "expiry": "expiry",
            "status": "status"
        }

        widths = {
            "brand": 105,
            "product": 175,
            "category": 120,
            "barcode": 120,
            "batch": 115,
            "remaining": 95,
            "stock": 90,
            "expiry": 110,
            "status": 100
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column]
            )
            self.tree.column(
                column,
                width=widths[column],
                anchor="center"
            )

        self.tree.tag_configure(
            "new",
            background="#F5FBF7"
        )
        self.tree.tag_configure(
            "in_use",
            background="#F6F1FC"
        )
        self.tree.tag_configure(
            "low",
            background="#F7EAFB"
        )

        scrollbar = ttk.Scrollbar(
            card,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.tree.pack(
            side="left",
            fill="x",
            expand=True
        )
        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.product_selected
        )


    # graph ---------------------------------------------

    def create_graph_section(self):
        outer = tk.Frame(
            self.dashboard_frame,
            bg=BG,
            padx=28,
            pady=10
        )
        outer.pack(fill="x")

        tk.Label(
            outer,
            text="♡ product analytics by barcode",
            bg=BG,
            fg=LAVENDER_DARK,
            font=("Arial", 13, "bold")
        ).pack(
            anchor="w",
            pady=7
        )

        self.graph_subtitle = tk.Label(
            outer,
            text="select a product above to view every batch with the same barcode",
            bg=BG,
            fg=MUTED,
            font=("Arial", 9)
        )
        self.graph_subtitle.pack(
            anchor="w",
            pady=8
        )

        graphs = tk.Frame(
            outer,
            bg=BG
        )
        graphs.pack(fill="x")

        left_panel = RoundedPanel(
            graphs,
            bg=CARD,
            parent_bg=BG,
            border=BORDER,
            radius=20,
            padding=10
        )
        left_panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=6
        )
        left_card = left_panel.body

        tk.Label(
            left_card,
            text="♡ usage by batch",
            bg=CARD,
            fg=LAVENDER_DARK,
            font=("Arial", 11, "bold")
        ).pack(
            anchor="w",
            padx=16,
            pady=12
        )

        left_area = tk.Frame(
            left_card,
            bg=GRAPH_BG
        )
        left_area.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        self.graph_canvas = tk.Canvas(
            left_area,
            bg=GRAPH_BG,
            highlightthickness=0,
            height=285
        )

        left_scrollbar = ttk.Scrollbar(
            left_area,
            orient="vertical",
            command=self.graph_canvas.yview
        )

        self.graph_canvas.configure(
            yscrollcommand=left_scrollbar.set
        )
        self.graph_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )
        left_scrollbar.pack(
            side="right",
            fill="y"
        )

        right_panel = RoundedPanel(
            graphs,
            bg=CARD,
            parent_bg=BG,
            border=BORDER,
            radius=20,
            padding=10
        )
        right_panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=6
        )
        right_card = right_panel.body

        tk.Label(
            right_card,
            text="♡ remaining level graph",
            bg=CARD,
            fg=LAVENDER_DARK,
            font=("Arial", 11, "bold")
        ).pack(
            anchor="w",
            padx=16,
            pady=12
        )

        right_area = tk.Frame(
            right_card,
            bg=GRAPH_BG
        )
        right_area.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        self.line_canvas = tk.Canvas(
            right_area,
            bg=GRAPH_BG,
            highlightthickness=0,
            height=285
        )
        self.line_canvas.pack(
            fill="both",
            expand=True
        )

        self.graph_canvas.bind(
            "<Configure>",
            self.redraw_graphs
        )
        self.line_canvas.bind(
            "<Configure>",
            self.redraw_graphs
        )


    def product_selected(self, event=None):
        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(
            selected[0],
            "values"
        )

        if not values:
            return

        self.selected_barcode = str(values[3])
        self.draw_usage_graph(self.selected_barcode)
        self.draw_remaining_graph(self.selected_barcode)


    def redraw_graphs(self, event=None):
        if self.selected_barcode:
            self.draw_usage_graph(self.selected_barcode)
            self.draw_remaining_graph(self.selected_barcode)


    def products_for_barcode(self, barcode):
        products = [
            product
            for product in get_products()
            if product_group_key(product) == barcode
        ]

        products.sort(
            key=lambda product: (
                1
                if product.get("product_type", "normal") == "unused"
                else 0,
                days_until_expiry(product.get("expiry_date")),
                str(product.get("batch_code", "")).lower()
            )
        )
        return products


    def display_status_for_graph(self, product, remaining):
        if product.get("product_type", "normal") == "unused":
            return "unused"
        return get_product_status(
            remaining,
            product.get("expiry_date")
        )


    def draw_usage_graph(self, barcode):
        self.graph_canvas.delete("all")
        products = self.products_for_barcode(barcode)

        if not products:
            self.graph_subtitle.config(
                text="no products found for this barcode"
            )
            return

        name = products[0].get("name", "")
        self.graph_subtitle.config(
            text=(
                f"{name}  •  barcode: {barcode}  •  "
                f"{len(products)} batch(es)"
            )
        )

        width = max(
            self.graph_canvas.winfo_width(),
            560
        )
        left = 105
        right = 100
        top = 20
        row_height = 56
        bar_height = 19
        usable_width = max(150, width - left - right)
        graph_height = top + len(products) * row_height + 25

        for index, product in enumerate(products):
            remaining = get_remaining_percentage(
                product.get("initial_weight"),
                product.get("current_weight")
            )
            usage = get_usage_percentage(
                product.get("initial_weight"),
                product.get("current_weight")
            )
            status = self.display_status_for_graph(
                product,
                remaining
            )
            batch = product.get("batch_code", "")
            y = top + index * row_height

            self.graph_canvas.create_text(
                8,
                y + 9,
                text=batch,
                anchor="w",
                fill=TEXT,
                font=("Arial", 8, "bold")
            )

            create_rounded_rectangle(
                self.graph_canvas,
                left,
                y,
                left + usable_width,
                y + bar_height,
                8,
                fill="#EEE8F6",
                outline=""
            )

            bar_width = usable_width * usage / 100
            if bar_width > 1:
                create_rounded_rectangle(
                    self.graph_canvas,
                    left,
                    y,
                    left + bar_width,
                    y + bar_height,
                    8,
                    fill=GRAPH_BAR_DARK,
                    outline=""
                )

            self.graph_canvas.create_text(
                left + usable_width + 8,
                y + 9,
                text=f"{usage}%",
                anchor="w",
                fill=TEXT,
                font=("Arial", 8, "bold")
            )

            self.graph_canvas.create_text(
                left,
                y + 35,
                text=(
                    f"{remaining}% remaining  •  "
                    f"{status.upper()}"
                ),
                anchor="w",
                fill=MUTED,
                font=("Arial", 7)
            )

        self.graph_canvas.configure(
            scrollregion=(0, 0, width, graph_height)
        )


    def draw_remaining_graph(self, barcode):
        self.line_canvas.delete("all")
        products = self.products_for_barcode(barcode)

        if not products:
            return

        width = max(self.line_canvas.winfo_width(), 560)
        height = max(self.line_canvas.winfo_height(), 285)
        left = 48
        right = 22
        top = 24
        bottom = 62
        graph_width = max(180, width - left - right)
        graph_height = max(130, height - top - bottom)

        for value in (0, 25, 50, 75, 100):
            y = top + graph_height - (graph_height * value / 100)
            self.line_canvas.create_line(
                left,
                y,
                left + graph_width,
                y,
                fill="#E8E0F0",
                dash=(3, 4)
            )
            self.line_canvas.create_text(
                left - 7,
                y,
                text=f"{value}%",
                anchor="e",
                fill=MUTED,
                font=("Arial", 7)
            )

        points = []
        count = len(products)

        for index, product in enumerate(products):
            remaining = get_remaining_percentage(
                product.get("initial_weight"),
                product.get("current_weight")
            )

            if count == 1:
                x = left + graph_width / 2
            else:
                x = left + graph_width * index / (count - 1)

            y = top + graph_height - (graph_height * remaining / 100)
            points.append((x, y, product, remaining))

        for index in range(len(points) - 1):
            x1, y1 = points[index][0:2]
            x2, y2 = points[index + 1][0:2]
            self.line_canvas.create_line(
                x1, y1, x2, y2,
                fill=GRAPH_BAR_DARK,
                width=3,
                smooth=True
            )

        for x, y, product, remaining in points:
            batch = product.get("batch_code", "")
            status = self.display_status_for_graph(
                product,
                remaining
            )

            self.line_canvas.create_oval(
                x - 5, y - 5, x + 5, y + 5,
                fill=GRAPH_BAR_DARK,
                outline=""
            )
            self.line_canvas.create_text(
                x,
                y - 15,
                text=f"{remaining}%",
                fill=TEXT,
                font=("Arial", 8, "bold")
            )
            self.line_canvas.create_text(
                x,
                top + graph_height + 18,
                text=batch,
                fill=MUTED,
                font=("Arial", 7),
                angle=35
            )
            self.line_canvas.create_text(
                x,
                top + graph_height + 45,
                text=status.upper(),
                fill=MUTED,
                font=("Arial", 7)
            )

        self.line_canvas.configure(
            scrollregion=(0, 0, width, height)
        )


    # unused products ---------------------------------------------

    def create_unused_table(self):
        page_header = tk.Frame(
            self.unused_page,
            bg=BG,
            padx=28,
            pady=22
        )
        page_header.pack(fill="x")

        tk.Label(
            page_header,
            text="♡  Unused Products",
            bg=BG,
            fg=LAVENDER_DARK,
            font=("Arial", 22, "bold")
        ).pack(anchor="w")

        tk.Label(
            page_header,
            text="manual tracking only • remaining percentage is never auto-decreased",
            bg=BG,
            fg=MUTED,
            font=("Arial", 9)
        ).pack(anchor="w", pady=4)

        outer = tk.Frame(
            self.unused_page,
            bg=BG,
            padx=28,
            pady=12
        )
        outer.pack(fill="x")

        tk.Label(
            outer,
            text="♡ unused product records",
            bg=BG,
            fg=LAVENDER_DARK,
            font=("Arial", 13, "bold")
        ).pack(
            anchor="w",
            pady=3
        )

        tk.Label(
            outer,
            text="manual tracking only • these products are never auto-decreased",
            bg=BG,
            fg=MUTED,
            font=("Arial", 8)
        ).pack(
            anchor="w",
            pady=7
        )

        card_panel = RoundedPanel(
            outer,
            bg=CARD,
            parent_bg=BG,
            border=BORDER,
            radius=20,
            padding=10
        )
        card_panel.pack(
            fill="x"
        )
        card = card_panel.body

        columns = (
            "brand",
            "product",
            "category",
            "barcode",
            "batch",
            "remaining",
            "last_used",
            "expiry",
            "status"
        )

        self.unused_tree = ttk.Treeview(
            card,
            columns=columns,
            show="headings",
            height=5
        )

        headings = {
            "brand": "brand",
            "product": "product",
            "category": "category",
            "barcode": "barcode",
            "batch": "batch code",
            "remaining": "remaining",
            "last_used": "last used",
            "expiry": "expiry",
            "status": "status"
        }

        widths = {
            "brand": 105,
            "product": 165,
            "category": 110,
            "barcode": 110,
            "batch": 110,
            "remaining": 90,
            "last_used": 115,
            "expiry": 110,
            "status": 90
        }

        for column in columns:
            self.unused_tree.heading(
                column,
                text=headings[column]
            )
            self.unused_tree.column(
                column,
                width=widths[column],
                anchor="center"
            )

        self.unused_tree.tag_configure(
            "unused",
            background="#FFF5FB"
        )

        scrollbar = ttk.Scrollbar(
            card,
            orient="vertical",
            command=self.unused_tree.yview
        )
        self.unused_tree.configure(
            yscrollcommand=scrollbar.set
        )
        self.unused_tree.pack(
            side="left",
            fill="x",
            expand=True
        )
        scrollbar.pack(
            side="right",
            fill="y"
        )


    # history ---------------------------------------------

    def create_history_table(self):
        page_header = tk.Frame(
            self.history_page,
            bg=BG,
            padx=28,
            pady=22
        )
        page_header.pack(fill="x")

        tk.Label(
            page_header,
            text="⌛  Inventory History",
            bg=BG,
            fg=LAVENDER_DARK,
            font=("Arial", 22, "bold")
        ).pack(anchor="w")

        tk.Label(
            page_header,
            text="used and expired normal products are stored here",
            bg=BG,
            fg=MUTED,
            font=("Arial", 9)
        ).pack(anchor="w", pady=4)

        outer = tk.Frame(
            self.history_page,
            bg=BG,
            padx=28,
            pady=12
        )
        outer.pack(fill="x")

        tk.Label(
            outer,
            text="⌛ used & expired products",
            bg=BG,
            fg=LAVENDER_DARK,
            font=("Arial", 13, "bold")
        ).pack(
            anchor="w",
            pady=7
        )

        card_panel = RoundedPanel(
            outer,
            bg=CARD,
            parent_bg=BG,
            border=BORDER,
            radius=20,
            padding=10
        )
        card_panel.pack(
            fill="x"
        )
        card = card_panel.body

        columns = (
            "brand",
            "product",
            "barcode",
            "batch",
            "remaining",
            "expiry",
            "status"
        )

        self.history_tree = ttk.Treeview(
            card,
            columns=columns,
            show="headings",
            height=5
        )

        headings = {
            "brand": "brand",
            "product": "product",
            "barcode": "barcode",
            "batch": "batch code",
            "remaining": "remaining",
            "expiry": "expiry",
            "status": "status"
        }

        widths = {
            "brand": 130,
            "product": 210,
            "barcode": 140,
            "batch": 140,
            "remaining": 110,
            "expiry": 130,
            "status": 120
        }

        for column in columns:
            self.history_tree.heading(
                column,
                text=headings[column]
            )
            self.history_tree.column(
                column,
                width=widths[column],
                anchor="center"
            )

        self.history_tree.tag_configure(
            "used",
            background=USED_COLOUR
        )
        self.history_tree.tag_configure(
            "expired",
            background=EXPIRED_COLOUR
        )

        scrollbar = ttk.Scrollbar(
            card,
            orient="vertical",
            command=self.history_tree.yview
        )
        self.history_tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.history_tree.pack(
            side="left",
            fill="x",
            expand=True
        )
        scrollbar.pack(
            side="right",
            fill="y"
        )


    # refresh ---------------------------------------------

    def run_inventory_cycle(self, simulate=True):
        # expiry and old status are checked before usage
        update_all_statuses()
        check_for_replacements()
        update_all_statuses()

        if simulate:
            simulate_product_usage()
            update_all_statuses()
            check_for_replacements()
            update_all_statuses()

        self.refresh_dashboard()
        send_inventory_telemetry()


    def automatic_update(self):
        try:
            self.run_inventory_cycle(
                simulate=True
            )

        except Exception as error:
            print(
                "automatic update error:",
                error
            )

        finally:
            self.root.after(
                UPDATE_INTERVAL_MS,
                self.automatic_update
            )


    def refresh_dashboard(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for item in self.unused_tree.get_children():
            self.unused_tree.delete(item)

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        products = get_products()

        active_rows = []
        unused_rows = []
        history_rows = []
        low_products = []

        counts = {
            "active": 0,
            "in use": 0,
            "low": 0,
            "new": 0,
            "history": 0
        }

        for product in products:
            remaining = get_remaining_percentage(
                product.get("initial_weight"),
                product.get("current_weight")
            )

            product_type = product.get(
                "product_type",
                "normal"
            )

            if product_type == "unused":
                unused_rows.append({
                    "id": product.get("id"),
                    "barcode": product.get("barcode", ""),
                    "brand": product.get("brand", ""),
                    "name": product.get("name", ""),
                    "category": product.get("category", ""),
                    "batch": product.get("batch_code", ""),
                    "expiry": product.get("expiry_date", ""),
                    "remaining": remaining,
                    "last_used": product.get("last_used_date", ""),
                    "status": "unused"
                })
                continue

            status = get_product_status(
                remaining,
                product.get("expiry_date")
            )

            row = {
                "id": product.get("id"),
                "barcode": product.get("barcode", ""),
                "brand": product.get("brand", ""),
                "name": product.get("name", ""),
                "category": product.get("category", ""),
                "batch": product.get("batch_code", ""),
                "expiry": product.get("expiry_date", ""),
                "remaining": remaining,
                "status": status,
                "stock": get_stock_status(status)
            }

            if status in ("used", "expired"):
                counts["history"] += 1
                history_rows.append(row)
                continue

            counts["active"] += 1
            counts[status] += 1

            if status == "low":
                low_products.append(row)

            active_rows.append(row)

        def active_sort_key(row):
            status_priority = {
                "in use": 0,
                "low": 0,
                "new": 1
            }.get(row["status"], 2)

            return (
                str(row["barcode"]).lower(),
                status_priority,
                days_until_expiry(row["expiry"]),
                str(row["batch"]).lower()
            )

        active_rows.sort(key=active_sort_key)
        unused_rows.sort(
            key=lambda row: (
                str(row["barcode"]).lower(),
                str(row["name"]).lower(),
                str(row["batch"]).lower()
            )
        )
        history_rows.sort(
            key=lambda row: (
                str(row["barcode"]).lower(),
                0 if row["status"] == "expired" else 1,
                row["expiry"],
                str(row["batch"]).lower()
            )
        )

        for row in active_rows:
            tag = row["status"].replace(" ", "_")
            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["brand"],
                    row["name"],
                    row["category"],
                    row["barcode"],
                    row["batch"],
                    f"{row['remaining']}%",
                    row["stock"],
                    row["expiry"],
                    row["status"].upper()
                ),
                tags=(tag,)
            )

        for row in unused_rows:
            self.unused_tree.insert(
                "",
                "end",
                iid=f"unused_{row['id']}",
                values=(
                    row["brand"],
                    row["name"],
                    row["category"],
                    row["barcode"],
                    row["batch"],
                    f"{row['remaining']}%",
                    row["last_used"] or "—",
                    row["expiry"],
                    "UNUSED"
                ),
                tags=("unused",)
            )

        for row in history_rows:
            self.history_tree.insert(
                "",
                "end",
                iid=f"history_{row['id']}",
                values=(
                    row["brand"],
                    row["name"],
                    row["barcode"],
                    row["batch"],
                    f"{row['remaining']}%",
                    row["expiry"],
                    row["status"].upper()
                ),
                tags=(row["status"],)
            )

        self.total_label.config(
            text=f"{counts['active']}"
        )
        self.in_use_label.config(
            text=f"{counts['in use']}"
        )
        self.low_label.config(
            text=f"{counts['low']}"
        )
        self.new_label.config(
            text=f"{counts['new']}"
        )
        self.history_label.config(
            text=f"{counts['history']}"
        )

        # unused product reminder ---------------------------------------------

        if unused_rows:
            unused_rows.sort(
                key=lambda row: (
                    row["last_used"] or "9999-99-99",
                    str(row["name"]).lower()
                )
            )

            reminder_lines = []

            for row in unused_rows[:3]:
                last_used = (
                    row["last_used"]
                    or "no last used date recorded"
                )

                if row["last_used"]:
                    reminder_lines.append(
                        f"♡ {row['name']} has not been used since {last_used}"
                    )
                else:
                    reminder_lines.append(
                        f"♡ {row['name']} has not been used • {last_used}"
                    )

            if len(unused_rows) > 3:
                reminder_lines.append(
                    f"♡ +{len(unused_rows) - 3} more unused product(s)"
                )

            self.unused_notice_label.config(
                text="\n".join(reminder_lines)
            )

            if not self.unused_notice_card.winfo_manager():
                self.unused_notice_card.pack(
                    fill="x",
                    pady=10
                )

        else:
            if self.unused_notice_card.winfo_manager():
                self.unused_notice_card.pack_forget()

        if low_products:
            low_products.sort(key=lambda row: row["remaining"])
            first = low_products[0]
            notification = (
                f"♡ low stock: {first['name']} - "
                f"{first['remaining']}% remaining"
            )

            if len(low_products) > 1:
                notification += (
                    f"  •  +{len(low_products) - 1} more"
                )

            self.notification_label.config(
                text=notification,
                fg=PINK_DARK
            )
        else:
            self.notification_label.config(
                text="♡ all active clinic products are looking good",
                fg=GREEN_DARK
            )

        if self.selected_barcode:
            self.draw_usage_graph(self.selected_barcode)
            self.draw_remaining_graph(self.selected_barcode)

        self.root.update_idletasks()
        self.update_scrollregion()


    # add product ---------------------------------------------

    def open_add_window(self):
        window = tk.Toplevel(
            self.root
        )
        window.title(
            "♡ add product"
        )
        window.geometry(
            "560x610"
        )
        window.configure(
            bg=BG
        )
        window.resizable(
            False,
            False
        )

        tk.Label(
            window,
            text="♡ add new product",
            bg=BG,
            fg=LAVENDER_DARK,
            font=("Arial", 19, "bold")
        ).pack(
            pady=20
        )

        tk.Label(
            window,
            text="same barcodes are allowed • every unit needs its own batch code",
            bg=BG,
            fg=MUTED,
            font=("Arial", 9)
        ).pack(
            pady=15
        )

        form = tk.Frame(
            window,
            bg=CARD,
            padx=24,
            pady=18,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        form.pack(
            padx=22,
            fill="both",
            expand=True
        )

        fields = [
            "barcode",
            "brand",
            "product name",
            "category",
            "batch code",
            "expiry date (yyyy-mm-dd)",
            "initial weight (g)"
        ]

        entries = {}

        for index, field in enumerate(fields):
            tk.Label(
                form,
                text=field,
                bg=CARD,
                fg=TEXT,
                font=("Arial", 9, "bold")
            ).grid(
                row=index,
                column=0,
                sticky="w",
                padx=7,
                pady=8
            )

            entry = tk.Entry(
                form,
                width=30,
                bg="#FFFBFE",
                fg=TEXT,
                relief="flat",
                highlightbackground=BORDER,
                highlightthickness=1,
                font=("Arial", 10)
            )
            entry.grid(
                row=index,
                column=1,
                padx=7,
                pady=8,
                ipady=5
            )

            entries[field] = entry

        entries["batch code"].insert(
            0,
            generate_batch_code()
        )

        def save():
            try:
                barcode = entries[
                    "barcode"
                ].get().strip()

                brand = entries[
                    "brand"
                ].get().strip()

                name = entries[
                    "product name"
                ].get().strip()

                category = entries[
                    "category"
                ].get().strip()

                batch = entries[
                    "batch code"
                ].get().strip()

                expiry = entries[
                    "expiry date (yyyy-mm-dd)"
                ].get().strip()

                initial_weight = float(
                    entries[
                        "initial weight (g)"
                    ].get().strip()
                )

                if not barcode:
                    raise ValueError(
                        "barcode is required"
                    )

                if not name:
                    raise ValueError(
                        "product name is required"
                    )

                if not batch:
                    raise ValueError(
                        "batch code is required"
                    )

                if batch_exists(batch):
                    raise ValueError(
                        "batch code already exists"
                    )

                datetime.strptime(
                    expiry,
                    "%Y-%m-%d"
                )

                if initial_weight <= 0:
                    raise ValueError(
                        "initial weight must be greater than 0"
                    )

                add_product(
                    barcode=barcode,
                    brand=brand,
                    name=name,
                    category=category,
                    batch_code=batch,
                    expiry_date=expiry,
                    initial_weight=initial_weight,
                    current_weight=initial_weight,
                    status="new",
                    product_type="normal",
                    replacement_created=0
                )

                self.run_inventory_cycle(
                    simulate=False
                )

                window.destroy()

                messagebox.showinfo(
                    "♡ product added",
                    f"{name} has been added to the inventory."
                )

            except ValueError as error:
                messagebox.showerror(
                    "invalid information",
                    str(error)
                )

            except Exception as error:
                messagebox.showerror(
                    "could not add product",
                    str(error)
                )

        tk.Button(
            window,
            text="♡ save product",
            command=save,
            bg=LAVENDER,
            fg=TEXT,
            activebackground=LAVENDER_DARK,
            activeforeground="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=26,
            pady=10,
            cursor="hand2"
        ).pack(
            pady=18
        )


    # add unused product ---------------------------------------------

    def open_add_unused_window(self):
        window = tk.Toplevel(self.root)
        window.title("♡ add unused product")
        window.geometry("590x720")
        window.configure(bg=BG)
        window.resizable(False, False)

        tk.Label(
            window,
            text="♡ add unused product",
            bg=BG,
            fg=LAVENDER_DARK,
            font=("Arial", 19, "bold")
        ).pack(pady=18)

        tk.Label(
            window,
            text="manual record • remaining level will not auto-decrease",
            bg=BG,
            fg=MUTED,
            font=("Arial", 9)
        ).pack(pady=12)

        form = tk.Frame(
            window,
            bg=CARD,
            padx=22,
            pady=15,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        form.pack(
            padx=22,
            fill="both",
            expand=True
        )

        fields = [
            "barcode",
            "brand",
            "product name",
            "category",
            "batch code",
            "remaining (%)",
            "last used date (yyyy-mm-dd)",
            "expiry date (yyyy-mm-dd)",
            "initial weight (g)"
        ]

        entries = {}

        for index, field in enumerate(fields):
            tk.Label(
                form,
                text=field,
                bg=CARD,
                fg=TEXT,
                font=("Arial", 9, "bold")
            ).grid(
                row=index,
                column=0,
                sticky="w",
                padx=7,
                pady=7
            )

            entry = tk.Entry(
                form,
                width=30,
                bg="#FFFBFE",
                fg=TEXT,
                relief="flat",
                highlightbackground=BORDER,
                highlightthickness=1,
                font=("Arial", 10)
            )
            entry.grid(
                row=index,
                column=1,
                padx=7,
                pady=7,
                ipady=5
            )
            entries[field] = entry

        entries["batch code"].insert(
            0,
            generate_batch_code()
        )
        entries["remaining (%)"].insert(0, "100")

        def save_unused():
            try:
                barcode = entries["barcode"].get().strip()
                brand = entries["brand"].get().strip()
                name = entries["product name"].get().strip()
                category = entries["category"].get().strip()
                batch = entries["batch code"].get().strip()
                remaining = float(
                    entries["remaining (%)"].get().strip()
                )
                last_used = entries[
                    "last used date (yyyy-mm-dd)"
                ].get().strip()
                expiry = entries[
                    "expiry date (yyyy-mm-dd)"
                ].get().strip()
                initial_weight = float(
                    entries["initial weight (g)"].get().strip()
                )

                if not barcode:
                    raise ValueError("barcode is required")
                if not name:
                    raise ValueError("product name is required")
                if not batch:
                    raise ValueError("batch code is required")
                if batch_exists(batch):
                    raise ValueError("batch code already exists")
                if remaining < 0 or remaining > 100:
                    raise ValueError(
                        "remaining percentage must be between 0 and 100"
                    )
                if initial_weight <= 0:
                    raise ValueError(
                        "initial weight must be greater than 0"
                    )

                if last_used:
                    datetime.strptime(last_used, "%Y-%m-%d")
                datetime.strptime(expiry, "%Y-%m-%d")

                current_weight = (
                    initial_weight *
                    remaining /
                    100
                )

                add_product(
                    barcode=barcode,
                    brand=brand,
                    name=name,
                    category=category,
                    batch_code=batch,
                    expiry_date=expiry,
                    initial_weight=initial_weight,
                    current_weight=current_weight,
                    status="unused",
                    product_type="unused",
                    last_used_date=last_used or None,
                    replacement_created=0
                )

                self.refresh_dashboard()
                send_inventory_telemetry()
                self.show_page(
                    "unused"
                )
                window.destroy()

                messagebox.showinfo(
                    "♡ unused product added",
                    f"{name} has been added as an unused product."
                )

            except ValueError as error:
                messagebox.showerror(
                    "invalid information",
                    str(error)
                )
            except Exception as error:
                messagebox.showerror(
                    "could not add unused product",
                    str(error)
                )

        tk.Button(
            window,
            text="♡ save unused product",
            command=save_unused,
            bg=PINK,
            fg=TEXT,
            activebackground=PINK_DARK,
            activeforeground="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=26,
            pady=10,
            cursor="hand2"
        ).pack(pady=16)


# start program ---------------------------------------------

if __name__ == "__main__":
    print("running build:", APP_BUILD)
    try:
        connect_cosmos()
        connect_azure()

        root = tk.Tk()
        app = BeautyClinicApp(
            root
        )
        root.mainloop()

    except Exception as error:
        print(
            "application error:",
            error
        )

        try:
            messagebox.showerror(
                "beauty clinic error",
                str(error)
            )
        except Exception:
            pass

    finally:
        try:
            disconnect_azure()
        except Exception:
            pass

        try:
            disconnect_cosmos()
        except Exception:
            pass
