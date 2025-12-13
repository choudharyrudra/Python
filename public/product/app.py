import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import queue
import time
import random
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Supabase Integration ---
from supabase import create_client, Client

SUPABASE_URL = "https://jppovracmwffwnbkesnl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpwcG92cmFjbXdmZnduYmtlc25sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjEyOTAyNzksImV4cCI6MjA3Njg2NjI3OX0.wiQ4Y4VkYUv3uSCcUHDOu80GxIF9pCB4SblAa55wtNE"

# --- Modern Dark Theme Palette ---
COLORS = {
    "bg": "#0f172a",          # Main Window Background
    "surface": "#1e293b",     # Cards/Panels
    "accent": "#38bdf8",      # Primary Action
    "text": "#f1f5f9",        # Primary Text
    "text_muted": "#94a3b8",  # Secondary Text
    "success": "#4ade80",     # Green
    "danger": "#f87171",      # Red
    "border": "#334155",      # Borders
    "input_bg": "#334155"     # Inputs
}

# --- Mock Session Classes for Custom Auth ---
class MockUser:
    def __init__(self, uid, email):
        self.id = uid
        self.email = email

class MockSession:
    def __init__(self, uid, email):
        self.user = MockUser(uid, email)

class LoginDialog(tk.Toplevel):
    """Handles User Login and Registration via Custom 'users' Table"""
    def __init__(self, parent, supabase: Client):
        super().__init__(parent)
        self.supabase = supabase
        self.session = None
        
        self.title("Login - Market Terminal")
        self.geometry("400x450")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        
        # Center styles
        style = ttk.Style()
        style.configure("Login.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Login.TButton", font=("Segoe UI", 10, "bold"))

        # UI Elements
        tk.Label(self, text="MARKET ACCESS", font=("Segoe UI", 18, "bold"), bg=COLORS["bg"], fg=COLORS["accent"]).pack(pady=(40, 20))
        
        tk.Label(self, text="Email", font=("Segoe UI", 10), bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(anchor="w", padx=40)
        self.email_entry = tk.Entry(self, bg=COLORS["input_bg"], fg=COLORS["text"], font=("Segoe UI", 11), borderwidth=0, insertbackground="white")
        self.email_entry.pack(fill=tk.X, padx=40, pady=(5, 15), ipady=5)

        tk.Label(self, text="Password", font=("Segoe UI", 10), bg=COLORS["bg"], fg=COLORS["text_muted"]).pack(anchor="w", padx=40)
        self.pass_entry = tk.Entry(self, bg=COLORS["input_bg"], fg=COLORS["text"], font=("Segoe UI", 11), borderwidth=0, insertbackground="white", show="*")
        self.pass_entry.pack(fill=tk.X, padx=40, pady=(5, 25), ipady=5)
        
        # Allow pressing Enter to Login
        self.pass_entry.bind("<Return>", lambda event: self.do_login())

        self.status_lbl = tk.Label(self, text="", bg=COLORS["bg"], fg=COLORS["danger"], font=("Segoe UI", 9))
        self.status_lbl.pack(pady=(0, 10))

        btn_frame = tk.Frame(self, bg=COLORS["bg"])
        btn_frame.pack(fill=tk.X, padx=40)

        ttk.Button(btn_frame, text="LOGIN", command=self.do_login, width=15).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="REGISTER", command=self.do_register, width=15).pack(side=tk.RIGHT)

    def do_login(self):
        email = self.email_entry.get().strip()
        password = self.pass_entry.get().strip()
        if not email or not password:
            self.status_lbl.config(text="Please fill all fields")
            return
        
        try:
            # Custom Login: Select from 'users' table
            response = self.supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                self.session = MockSession(user_data['id'], user_data['email'])
                self.destroy()
            else:
                self.status_lbl.config(text="Invalid email or password")
                
        except Exception as e:
            self.status_lbl.config(text=f"Login failed: {str(e)}")

    def do_register(self):
        email = self.email_entry.get().strip()
        password = self.pass_entry.get().strip()
        if not email or not password:
            self.status_lbl.config(text="Please fill all fields")
            return

        try:
            # Custom Register: Insert into 'users' table
            # First check if email exists to give a better error message
            check = self.supabase.table("users").select("id").eq("email", email).execute()
            if check.data:
                self.status_lbl.config(text="Email already registered")
                return

            data = {"email": email, "password": password}
            response = self.supabase.table("users").insert(data).execute()
            
            if response.data:
                user_data = response.data[0]
                self.session = MockSession(user_data['id'], user_data['email'])
                messagebox.showinfo("Success", "Registration successful! Logging in...")
                self.destroy()
            else:
                 self.status_lbl.config(text="Registration failed (No data returned)")

        except Exception as e:
            self.status_lbl.config(text=f"Register failed: {str(e)}")


class UserInfoWindow(tk.Toplevel):
    """Displays User Profile, Holdings, and Transaction History"""
    def __init__(self, parent, email, holdings, transactions):
        super().__init__(parent)
        self.parent = parent
        self.title("User Profile")
        self.geometry("900x700")
        self.configure(bg=COLORS["bg"])
        self.transient(parent)

        # Header
        header = tk.Frame(self, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=25, pady=20)
        tk.Label(header, text="USER PROFILE", font=("Segoe UI", 16, "bold"), fg=COLORS["accent"], bg=COLORS["bg"]).pack(side=tk.LEFT)
        
        # User Details
        info_card = ttk.Frame(self, style="Card.TFrame")
        info_card.pack(fill=tk.X, padx=25, pady=(0, 20))
        
        tk.Label(info_card, text="EMAIL ADDRESS", font=("Segoe UI", 8, "bold"), fg=COLORS["text_muted"], bg=COLORS["surface"]).pack(anchor="w", padx=15, pady=(15, 5))
        tk.Label(info_card, text=email, font=("Segoe UI", 12), fg=COLORS["text"], bg=COLORS["surface"]).pack(anchor="w", padx=15, pady=(0, 15))

        # Content Split
        content = tk.Frame(self, bg=COLORS["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

        # Holdings (Left)
        h_frame = ttk.Frame(content, style="Card.TFrame")
        h_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(h_frame, text="CURRENT HOLDINGS", font=("Segoe UI", 10, "bold"), fg=COLORS["text_muted"], bg=COLORS["surface"]).pack(anchor="w", padx=15, pady=15)
        
        h_tree = ttk.Treeview(h_frame, columns=("ticker", "qty"), show="headings", height=10)
        h_tree.heading("ticker", text="TICKER", anchor="w")
        h_tree.heading("qty", text="QUANTITY", anchor="e")
        h_tree.column("ticker", anchor="w")
        h_tree.column("qty", anchor="e")
        h_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        for ticker, qty in holdings.items():
            if qty > 0:
                h_tree.insert("", tk.END, values=(ticker, qty))

        # Transactions (Right)
        t_frame = ttk.Frame(content, style="Card.TFrame")
        t_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(t_frame, text="TRANSACTION HISTORY", font=("Segoe UI", 10, "bold"), fg=COLORS["text_muted"], bg=COLORS["surface"]).pack(anchor="w", padx=15, pady=15)
        
        t_tree = ttk.Treeview(t_frame, columns=("date", "ticker", "side", "price", "qty", "total"), show="headings", height=10)
        cols = ["Date", "Ticker", "Side", "Price", "Qty", "Total"]
        for c in cols:
            t_tree.heading(c.lower(), text=c.upper(), anchor="w" if c in ["Date", "Ticker"] else "e")
            t_tree.column(c.lower(), width=80 if c not in ["Date"] else 120, anchor="w" if c in ["Date", "Ticker"] else "e")
            
        t_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        for tx in transactions:
            # Format date for cleaner view
            date_str = str(tx.get("Date", ""))
            if "T" in date_str:
                # Convert ISO format to simpler YYYY-MM-DD HH:MM
                try:
                    date_str = date_str.replace("T", " ")[:16]
                except: pass

            t_tree.insert("", tk.END, values=(
                date_str,
                tx.get("Ticker"),
                tx.get("Side"),
                f"{tx.get('Price', 0):.2f}",
                tx.get("Quantity"),
                f"{tx.get('Total', 0):.2f}"
            ))


class StockApp(tk.Tk):
    INDICES = {
        "Nifty 50 (NSE)": "^NSEI",
        "Sensex (BSE)": "^BSESN",
        "Bank Nifty": "^NSEBANK",
        "Nifty IT": "^CNXIT"
    }

    TIMEFRAMES = {
        "1 Day": ("1d", "5m"),
        "5 Days": ("5d", "15m"),
        "1 Month": ("1mo", "30m"),
        "6 Months": ("6mo", "1d"),
        "1 Year": ("1y", "1d"),
        "5 Years": ("5y", "1wk")
    }

    SUMMARY_FIELDS = [
        ("Open", ("open", "regularMarketOpen")),
        ("Day High", ("day_high", "regularMarketDayHigh")),
        ("Day Low", ("day_low", "regularMarketDayLow")),
        ("Prev Close", ("previous_close", "regularMarketPreviousClose")),
        ("Volume", ("volume", "regularMarketVolume")),
        ("52W High", ("year_high", "fiftyTwoWeekHigh")),
        ("52W Low", ("year_low", "fiftyTwoWeekLow")),
        ("Market Cap", ("market_cap", "marketCap"))
    ]

    def __init__(self, supabase_client, session):
        super().__init__()
        self.supabase = supabase_client
        self.user = session.user
        
        self.title("Market Terminal - Connected")
        self.geometry("1280x800")
        self.configure(bg=COLORS["bg"])

        # --- State & Data ---
        self.data_queue = queue.Queue()
        self.fetch_thread = None
        self.fetching = False

        self.timestamps = []
        self.prices = []
        self.seen_points = set()
        self.transactions = []  # Local cache of history
        self.holdings_cache = {} # Local cache of holdings: {ticker: qty}

        self.watchlist = list(self.INDICES.values())
        self.watchlist_data = {}
        self.watchlist_refreshing = False

        self.price_var = tk.StringVar(value="--")
        self.change_var = tk.StringVar(value="--")
        self.status_var = tk.StringVar(value="Ready")
        self.ticker_var = tk.StringVar(value="^NSEI")
        self.interval_var = tk.StringVar(value="1m")
        self.timeframe_var = tk.StringVar(value="1 Day")
        self.summary_labels = {}

        # --- Initialization ---
        self._setup_styles()
        self._build_layout()
        self._init_plot()
        
        # Load DB Data
        self._load_user_data()

        self._schedule_queue_check()
        self._load_historical_data()
        self.refresh_watchlist()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["surface"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("Muted.TLabel", foreground=COLORS["text_muted"])
        style.configure("Card.TLabel", background=COLORS["surface"])
        style.configure("TButton", background=COLORS["surface"], foreground=COLORS["accent"], borderwidth=0, focuscolor=COLORS["accent"], font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", COLORS["border"])])
        style.configure("Accent.TButton", background=COLORS["accent"], foreground=COLORS["bg"])
        style.map("Accent.TButton", background=[("active", "#7dd3fc")])
        style.configure("TCombobox", fieldbackground=COLORS["input_bg"], background=COLORS["surface"], foreground=COLORS["text"], arrowcolor=COLORS["accent"], borderwidth=0)
        style.map("TCombobox", fieldbackground=[("readonly", COLORS["input_bg"])])
        style.configure("Treeview", background=COLORS["surface"], fieldbackground=COLORS["surface"], foreground=COLORS["text"], borderwidth=0, font=("Segoe UI", 10), rowheight=28)
        style.configure("Treeview.Heading", background=COLORS["bg"], foreground=COLORS["text_muted"], borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", COLORS["border"])], foreground=[("selected", COLORS["accent"])])

    def _build_layout(self):
        header = tk.Frame(self, bg=COLORS["bg"], height=60)
        header.pack(fill=tk.X, padx=25, pady=20)
        
        tk.Label(header, text="MARKET TERMINAL", font=("Segoe UI", 14, "bold"), fg=COLORS["accent"], bg=COLORS["bg"]).pack(side=tk.LEFT)

        controls = tk.Frame(header, bg=COLORS["bg"])
        controls.pack(side=tk.RIGHT)

        search_frame = tk.Frame(controls, bg=COLORS["input_bg"], padx=1, pady=1)
        search_frame.pack(side=tk.LEFT, padx=(0, 15))
        self.ticker_entry = tk.Entry(search_frame, textvariable=self.ticker_var, bg=COLORS["input_bg"], fg=COLORS["text"], font=("Segoe UI", 11), borderwidth=0, insertbackground=COLORS["accent"], width=12)
        self.ticker_entry.pack(side=tk.LEFT, padx=8, pady=4)
        self.ticker_entry.bind("<Return>", lambda _: self._load_historical_data())
        
        ttk.Button(controls, text="GO", command=self._load_historical_data, width=4).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(controls, text="RANGE", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0,5))
        tf_box = ttk.Combobox(controls, textvariable=self.timeframe_var, values=list(self.TIMEFRAMES.keys()), state="readonly", width=10)
        tf_box.pack(side=tk.LEFT, padx=(0, 20))
        tf_box.bind("<<ComboboxSelected>>", lambda _: self._load_historical_data())

        ttk.Label(controls, text="LIVE", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0,5))
        int_box = ttk.Combobox(controls, textvariable=self.interval_var, values=["1m", "2m", "5m", "15m"], state="readonly", width=5)
        int_box.pack(side=tk.LEFT, padx=(0, 15))
        
        self.start_button = ttk.Button(controls, text="▶ START", style="Accent.TButton", command=self.start_fetch)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(controls, text="■ STOP", command=self.stop_fetch, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="⬇ CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        
        # --- Added Profile and Trial Buttons ---
        ttk.Button(controls, text="Profile", command=self.open_user_info, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Trial", command=self.open_trial_mode, width=8).pack(side=tk.LEFT, padx=5)

        main_container = tk.Frame(self, bg=COLORS["bg"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

        sidebar = ttk.Frame(main_container, style="Card.TFrame", width=320)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        sidebar.pack_propagate(False)

        sb_header = tk.Frame(sidebar, bg=COLORS["surface"])
        sb_header.pack(fill=tk.X, padx=15, pady=15)
        tk.Label(sb_header, text="WATCHLIST", font=("Segoe UI", 10, "bold"), fg=COLORS["text_muted"], bg=COLORS["surface"]).pack(side=tk.LEFT)

        wl_actions = tk.Frame(sidebar, bg=COLORS["surface"])
        wl_actions.pack(fill=tk.X, padx=15, pady=(0, 10))
        self.watchlist_entry = tk.Entry(wl_actions, bg=COLORS["input_bg"], fg=COLORS["text"], borderwidth=0, insertbackground=COLORS["text"])
        self.watchlist_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0,5))
        self.watchlist_entry.bind("<Return>", lambda _: self.add_to_watchlist())
        tk.Button(wl_actions, text="+", bg=COLORS["accent"], fg=COLORS["bg"], font=("Arial", 12, "bold"), borderwidth=0, command=self.add_to_watchlist, cursor="hand2", width=3).pack(side=tk.LEFT)

        tree_frame = tk.Frame(sidebar, bg=COLORS["surface"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.watchlist_tree = ttk.Treeview(tree_frame, columns=("ticker", "last", "change"), show="headings", selectmode="browse")
        self.watchlist_tree.heading("ticker", text="SYMBOL", anchor="w")
        self.watchlist_tree.heading("last", text="PRICE", anchor="e")
        self.watchlist_tree.heading("change", text="%", anchor="e")
        self.watchlist_tree.column("ticker", width=90)
        self.watchlist_tree.column("last", width=80, anchor="e")
        self.watchlist_tree.column("change", width=70, anchor="e")
        self.watchlist_tree.pack(fill=tk.BOTH, expand=True)
        self.watchlist_tree.tag_configure("gain", foreground=COLORS["success"])
        self.watchlist_tree.tag_configure("loss", foreground=COLORS["danger"])
        self.watchlist_tree.tag_configure("neutral", foreground=COLORS["text_muted"])
        self.watchlist_tree.bind("<<TreeviewSelect>>", self._on_watchlist_select)

        btm_actions = tk.Frame(sidebar, bg=COLORS["surface"])
        btm_actions.pack(fill=tk.X, padx=15, pady=15, side=tk.BOTTOM)
        ttk.Button(btm_actions, text="Refresh", command=self.refresh_watchlist).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(btm_actions, text="Remove", command=self.remove_from_watchlist).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5,0))

        content = tk.Frame(main_container, bg=COLORS["bg"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        stats_card = ttk.Frame(content, style="Card.TFrame")
        stats_card.pack(fill=tk.X, pady=(0, 20))
        
        p_header = tk.Frame(stats_card, bg=COLORS["surface"])
        p_header.pack(fill=tk.X, padx=25, pady=20)
        self.price_label = tk.Label(p_header, textvariable=self.price_var, font=("Segoe UI", 36, "bold"), bg=COLORS["surface"], fg=COLORS["text"])
        self.price_label.pack(side=tk.LEFT)
        self.change_label = tk.Label(p_header, textvariable=self.change_var, font=("Segoe UI", 18), bg=COLORS["surface"], fg=COLORS["text_muted"])
        self.change_label.pack(side=tk.LEFT, padx=(25, 0), pady=(12, 0))
        tk.Label(p_header, textvariable=self.status_var, font=("Segoe UI", 9), bg=COLORS["surface"], fg=COLORS["text_muted"]).pack(side=tk.RIGHT, pady=(15,0))

        trade_box = tk.Frame(p_header, bg=COLORS["surface"])
        trade_box.pack(side=tk.RIGHT, pady=(12, 0), padx=20)
        ttk.Button(trade_box, text="BUY", style="Accent.TButton", command=lambda: self._trade("BUY")).pack(side=tk.LEFT, padx=5)
        ttk.Button(trade_box, text="SELL", command=lambda: self._trade("SELL")).pack(side=tk.LEFT, padx=5)

        grid_frame = tk.Frame(stats_card, bg=COLORS["surface"])
        grid_frame.pack(fill=tk.X, padx=25, pady=(0, 25))
        for idx, (label, _) in enumerate(self.SUMMARY_FIELDS):
            col, row = idx % 4, idx // 4
            f = tk.Frame(grid_frame, bg=COLORS["surface"])
            f.grid(row=row, column=col, sticky="ew", padx=10, pady=10)
            tk.Label(f, text=label.upper(), font=("Segoe UI", 8, "bold"), fg=COLORS["text_muted"], bg=COLORS["surface"]).pack(anchor="w")
            val_lbl = tk.Label(f, text="--", font=("Segoe UI", 12), fg=COLORS["text"], bg=COLORS["surface"])
            val_lbl.pack(anchor="w")
            self.summary_labels[label] = val_lbl
        for c in range(4): grid_frame.columnconfigure(c, weight=1)

        self.plot_container = ttk.Frame(content, style="Card.TFrame")
        self.plot_container.pack(fill=tk.BOTH, expand=True)

    def _init_plot(self):
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.figure.patch.set_facecolor(COLORS["surface"])
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(COLORS["surface"])
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.spines['bottom'].set_visible(True)
        self.ax.spines['bottom'].set_color(COLORS["border"])
        self.ax.spines['left'].set_visible(True)
        self.ax.spines['left'].set_color(COLORS["border"])
        self.ax.tick_params(axis='x', colors=COLORS["text_muted"], labelsize=9)
        self.ax.tick_params(axis='y', colors=COLORS["text_muted"], labelsize=9)
        self.ax.grid(True, color=COLORS["border"], linestyle='--', linewidth=0.5, alpha=0.4)
        self.line, = self.ax.plot([], [], color=COLORS["accent"], linewidth=2)
        self.fill_area = None
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    def _update_plot(self):
        if not self.prices:
            return
        x_data = range(len(self.prices))
        self.line.set_data(x_data, self.prices)
        if self.fill_area:
            self.fill_area.remove()
        min_price = min(self.prices)
        padding = (max(self.prices) - min_price) * 0.1
        base_val = min_price - padding
        self.fill_area = self.ax.fill_between(x_data, self.prices, base_val, color=COLORS["accent"], alpha=0.1)
        max_points = len(self.timestamps)
        if max_points:
            step = max(1, max_points // 8)
            xticks = list(range(0, max_points, step))
            self.ax.set_xticks(xticks)
            xticklabels = [self.timestamps[i] for i in xticks]
            self.ax.set_xticklabels(xticklabels, rotation=0, ha="center", fontsize=9, color=COLORS["text_muted"])
        self.ax.set_ylim(min(self.prices) * 0.999, max(self.prices) * 1.001)
        self.ax.set_xlim(0, max(len(self.prices) - 1, 1))
        self.canvas.draw_idle()

    def start_fetch(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            messagebox.showerror("Input Error", "Please enter a ticker symbol.")
            return
        if self.fetching:
            return
        self.fetching = True
        self.timestamps.clear()
        self.prices.clear()
        self.seen_points.clear()
        self.status_var.set(f"LIVE: {ticker}")
        self.price_var.set("--")
        self.change_var.set("--")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.fetch_thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self.fetch_thread.start()

    def stop_fetch(self):
        if not self.fetching:
            return
        self.fetching = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Stopped")

    def _fetch_loop(self):
        ticker_symbol = self.ticker_var.get().strip().upper()
        interval = self.interval_var.get()
        ticker = yf.Ticker(ticker_symbol)
        while self.fetching:
            try:
                data = ticker.history(period="1d", interval=interval)
                if not data.empty:
                    new_points = []
                    for idx, price in data["Close"].items():
                        ts_obj = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else datetime.fromtimestamp(idx)
                        idx_key = ts_obj.isoformat()
                        if idx_key in self.seen_points:
                            continue
                        self.seen_points.add(idx_key)
                        new_points.append((ts_obj.strftime("%H:%M"), float(price)))
                    if new_points:
                        self.data_queue.put(("BULK", new_points))
                    else:
                        last_idx = data.index[-1]
                        ts_obj = last_idx.to_pydatetime() if hasattr(last_idx, "to_pydatetime") else datetime.fromtimestamp(last_idx)
                        last_price = float(data["Close"].iloc[-1])
                        self.data_queue.put(("LAST", (ts_obj.strftime("%H:%M"), last_price)))
                else:
                    self.data_queue.put(("EMPTY", None))
            except Exception as exc:
                self.data_queue.put(("ERROR", exc))
            time.sleep(15)

    def _schedule_queue_check(self):
        self.after(500, self._process_queue)

    def _process_queue(self):
        try:
            while True:
                item = self.data_queue.get_nowait()
                tag = item[0]
                if tag == "ERROR":
                    self.status_var.set(f"Error: {item[1]}")
                    continue
                if tag == "EMPTY":
                    continue
                if tag == "BULK":
                    for timestamp, price in item[1]:
                        self.timestamps.append(timestamp)
                        self.prices.append(price)
                    if len(self.timestamps) > 300:
                        self.timestamps = self.timestamps[-300:]
                        self.prices = self.prices[-300:]
                    self._update_plot()
                    self._update_live_labels(self.prices[-1])
                    continue
                if tag == "LAST" and item[1]:
                    _, price = item[1]
                    self._update_live_labels(price)
        except queue.Empty:
            pass
        finally:
            self._schedule_queue_check()

    def _update_live_labels(self, price):
        self.price_var.set(self._fmt_price(price))
        if len(self.prices) > 1 and self.prices[-2] != 0:
            change = price - self.prices[-2]
            change_pct = (change / self.prices[-2]) * 100
            sign = "+" if change >= 0 else "-"
            self.change_var.set(f"{sign}{abs(change):,.2f} ({sign}{abs(change_pct):.2f}%)")
            self.change_label.config(fg=COLORS["success"] if change >= 0 else COLORS["danger"])

    def _load_historical_data(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            return
        if self.fetching:
            self.stop_fetch()
        timeframe = self.timeframe_var.get()
        period, interval = self.TIMEFRAMES.get(timeframe, ("1d", "5m"))
        self.status_var.set(f"Loading {ticker}...")

        def worker(symbol, label, per, inter):
            try:
                data = yf.download(symbol, period=per, interval=inter, progress=False, auto_adjust=False)
            except Exception as exc:
                self.after(0, lambda: self.status_var.set(f"Error: {exc}"))
                return
            ticker_obj = yf.Ticker(symbol)
            try:
                fast_info = ticker_obj.fast_info
            except Exception:
                fast_info = {}
            self.after(0, lambda: self._apply_historical_data(symbol, label, inter, data, fast_info))

        threading.Thread(target=worker, args=(ticker, timeframe, period, interval), daemon=True).start()

    def _apply_historical_data(self, ticker, timeframe, interval, data, fast_info):
        if data.empty:
            self.status_var.set("No data available")
            return
        is_intraday = interval.endswith("m") or interval.endswith("h")
        self.timestamps = []
        self.prices = []
        for idx, price in data["Close"].items():
            label = self._format_timestamp_label(idx, interval, is_intraday)
            self.timestamps.append(label)
            self.prices.append(float(price))
        if len(self.timestamps) > 600:
            self.timestamps = self.timestamps[-600:]
            self.prices = self.prices[-600:]
        self._update_plot()
        last_price = self.prices[-1]
        self.price_var.set(self._fmt_price(last_price))
        prev_close = self._extract_value(fast_info, "previous_close", "regularMarketPreviousClose")
        if prev_close:
            change = last_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0
            sign = "+" if change >= 0 else "-"
            self.change_var.set(f"{sign}{abs(change):,.2f} ({sign}{abs(change_pct):.2f}%)")
            self.change_label.config(fg=COLORS["success"] if change >= 0 else COLORS["danger"])
        else:
            self.change_var.set("--")
            self.change_label.config(fg=COLORS["text_muted"])
        self._update_summary_panel(fast_info)
        self.status_var.set(f"Ready")

    def _update_summary_panel(self, fast_info):
        info = fast_info or {}
        for label, keys in self.SUMMARY_FIELDS:
            value = self._extract_value(info, *keys)
            if label in {"Volume", "Market Cap"}:
                text = self._fmt_large(value)
            else:
                text = self._fmt_price(value)
            self.summary_labels[label].config(text=text)

    def refresh_watchlist(self):
        if self.watchlist_refreshing:
            return
        if not self.watchlist:
            self.watchlist_tree.delete(*self.watchlist_tree.get_children())
            return
        self.watchlist_refreshing = True
        threading.Thread(target=self._watchlist_worker, daemon=True).start()

    def _watchlist_worker(self):
        results = {}
        for ticker in self.watchlist:
            results[ticker] = self._fetch_quote_snapshot(ticker)
        self.after(0, lambda: self._finalize_watchlist_refresh(results))

    def _finalize_watchlist_refresh(self, results):
        self.watchlist_refreshing = False
        self._update_watchlist_ui(results)

    def _update_watchlist_ui(self, results):
        self.watchlist_data.update(results)
        selected = self.watchlist_tree.selection()
        selected_id = selected[0] if selected else None
        self.watchlist_tree.delete(*self.watchlist_tree.get_children())
        for ticker in self.watchlist:
            data = self.watchlist_data.get(ticker, {})
            price_text = self._fmt_price(data.get("last"))
            change_pct = data.get("change_pct")
            change_text = f"{change_pct:+.2f}%" if isinstance(change_pct, (int, float)) else "--"
            tag = "neutral"
            if isinstance(change_pct, (int, float)):
                tag = "gain" if change_pct >= 0 else "loss"
            self.watchlist_tree.insert("", tk.END, iid=ticker, values=(ticker, price_text, change_text), tags=(tag,))
        if selected_id and selected_id in self.watchlist:
            self.watchlist_tree.selection_set(selected_id)
        elif self.watchlist:
            self.watchlist_tree.selection_set(self.watchlist[0])

    def add_to_watchlist(self):
        ticker = self.watchlist_entry.get().strip().upper()
        if not ticker:
            return
        if ticker in self.watchlist:
            return
        self.watchlist.append(ticker)
        self.watchlist_entry.delete(0, tk.END)
        self.refresh_watchlist()

    def remove_from_watchlist(self):
        selection = self.watchlist_tree.selection()
        if not selection:
            return
        ticker = selection[0]
        if ticker in self.watchlist:
            self.watchlist.remove(ticker)
            self.watchlist_data.pop(ticker, None)
            self.refresh_watchlist()

    def _on_watchlist_select(self, _event=None):
        selection = self.watchlist_tree.selection()
        if not selection:
            return
        ticker = selection[0]
        if ticker == self.ticker_var.get().upper():
            return
        self.ticker_var.set(ticker)
        self._load_historical_data()

    def _fetch_quote_snapshot(self, ticker):
        snapshot = {"last": None, "change": None, "change_pct": None}
        ticker_obj = yf.Ticker(ticker)
        try:
            info = ticker_obj.fast_info
        except Exception:
            info = {}
        last_price = self._extract_value(info, "last_price", "lastPrice", "regularMarketPrice")
        prev_close = self._extract_value(info, "previous_close", "regularMarketPreviousClose")
        if last_price is None or prev_close is None:
            try:
                hist = ticker_obj.history(period="2d", interval="1d")
                if not hist.empty:
                    last_price = float(hist["Close"].iloc[-1])
                    if len(hist) > 1:
                        prev_close = float(hist["Close"].iloc[-2])
            except Exception:
                pass
        snapshot["last"] = last_price
        if last_price is not None and prev_close:
            change = last_price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0
            snapshot["change"] = change
            snapshot["change_pct"] = change_pct
        return snapshot

    # --- Supabase & Logic ---

    def _load_user_data(self):
        """Loads existing transactions and holdings from Supabase"""
        try:
            # 1. Load History
            resp = self.supabase.table("transactions").select("*").eq("user_id", self.user.id).order("created_at", desc=True).execute()
            for item in resp.data:
                # Map DB fields to UI fields if necessary, or just store raw
                self.transactions.append({
                    "Date": item["created_at"],
                    "Ticker": item["ticker"],
                    "Side": item["side"],
                    "Price": float(item["price"]),
                    "Quantity": item["quantity"],
                    "Total": float(item["total"])
                })
            
            # 2. Load Holdings
            resp_h = self.supabase.table("holdings").select("*").eq("user_id", self.user.id).execute()
            for h in resp_h.data:
                self.holdings_cache[h["ticker"]] = h["quantity"]
                
        except Exception as e:
            messagebox.showerror("DB Error", f"Failed to load user data: {e}")

    def _trade(self, side):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            return
            
        # Validate price
        try:
            price_str = self.price_var.get().replace(",", "")
            if price_str == "--":
                messagebox.showerror("Trade Error", "No price data available.")
                return
            price = float(price_str)
        except ValueError:
             messagebox.showerror("Trade Error", "Invalid price data.")
             return

        # Check holdings for SELL
        current_qty = self.holdings_cache.get(ticker, 0)
        
        qty = simpledialog.askinteger("Trade", f"Enter quantity to {side} {ticker}:\n(Owned: {current_qty})", parent=self, minvalue=1)
        if not qty:
            return

        if side == "SELL" and qty > current_qty:
            messagebox.showerror("Trade Error", f"Insufficient holdings.\nYou own {current_qty}, tried to sell {qty}.")
            return

        total = price * qty
        timestamp = datetime.now().isoformat()

        # --- Execute DB Transaction in Thread ---
        def db_worker():
            try:
                # 1. Insert Transaction
                tx_data = {
                    "user_id": self.user.id,
                    "ticker": ticker,
                    "side": side,
                    "price": price,
                    "quantity": qty,
                    "total": total
                }
                self.supabase.table("transactions").insert(tx_data).execute()

                # 2. Update Holdings
                # We re-fetch to be safe or use upsert logic
                # Optimistic calculation:
                new_qty = current_qty + qty if side == "BUY" else current_qty - qty
                
                # Upsert holding
                # Note: 'upsert' works if we have a primary key or unique constraint. 
                # We have unique(user_id, ticker).
                hold_data = {
                    "user_id": self.user.id,
                    "ticker": ticker,
                    "quantity": new_qty
                }
                # If new_qty is 0, we could delete, but keeping 0 is fine.
                self.supabase.table("holdings").upsert(hold_data, on_conflict="user_id, ticker").execute()

                # 3. Update UI (Main Thread)
                self.after(0, lambda: self._on_trade_success(ticker, side, qty, price, total, new_qty, timestamp))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Trade Failed", f"Database Error: {e}"))

        threading.Thread(target=db_worker, daemon=True).start()

    def _on_trade_success(self, ticker, side, qty, price, total, new_qty, timestamp):
        # Update local caches
        self.holdings_cache[ticker] = new_qty
        self.transactions.insert(0, {
            "Date": timestamp,
            "Ticker": ticker,
            "Side": side,
            "Price": price,
            "Quantity": qty,
            "Total": total
        })
        messagebox.showinfo("Trade Executed", f"{side} Order Filled:\n{qty} {ticker} @ {price:.2f}\nTotal: {total:.2f}\nNew Balance: {new_qty}")

    def export_csv(self):
        if not self.transactions:
            messagebox.showwarning("Export", "No transactions to export.")
            return
            
        df = pd.DataFrame(self.transactions)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Trades"
        )
        
        if file_path:
            try:
                df.to_csv(file_path, index=False)
                messagebox.showinfo("Export Success", f"Saved {len(df)} transactions to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save file:\n{e}")

    def open_trial_mode(self):
        TrialWindow(self)

    def open_user_info(self):
        UserInfoWindow(self, self.user.email, self.holdings_cache, self.transactions)

    @staticmethod
    def _extract_value(info, *keys):
        if not isinstance(info, dict):
            return None
        for key in keys:
            if key in info and info[key] is not None:
                return info[key]
        return None

    @staticmethod
    def _fmt_price(value):
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return "--"

    @staticmethod
    def _fmt_large(value):
        try:
            num = float(value)
        except (TypeError, ValueError):
            return "--"
        suffixes = ["", "K", "M", "B", "T"]
        idx = 0
        while abs(num) >= 1000 and idx < len(suffixes) - 1:
            num /= 1000.0
            idx += 1
        return f"{num:,.2f}{suffixes[idx]}"

    @staticmethod
    def _format_timestamp_label(ts, interval, is_intraday):
        if is_intraday:
            return ts.strftime("%H:%M")
        if interval == "1d":
            return ts.strftime("%d %b")
        if interval == "1wk":
            return ts.strftime("%b %Y")
        return ts.strftime("%b %Y")


# --- Simulated Data Model ---
class SimulatedTicker:
    """Represents a single stock in the trial simulation."""
    def __init__(self, symbol, base_price):
        self.symbol = symbol
        self.price = base_price * random.uniform(0.95, 1.05)
        self.prev_close = self.price
        self.open_price = self.price
        self.day_high = self.price
        self.day_low = self.price
        self.volume = 0
        
        self.history = []
        self.timestamps = []
        
        # Generate initial history so chart isn't empty
        now = datetime.now()
        for i in range(50):
            t = now - timedelta(minutes=50-i)
            # Slight random walk for history
            p = self.price * (1 + random.uniform(-0.01, 0.01))
            self.history.append(p)
            self.timestamps.append(t.strftime("%H:%M"))
        self.price = self.history[-1]

    def tick(self):
        """Updates the price based on a random walk."""
        change_pct = random.uniform(-0.003, 0.003) # +/- 0.3% volatility
        self.price *= (1 + change_pct)
        self.day_high = max(self.day_high, self.price)
        self.day_low = min(self.day_low, self.price)
        self.volume += random.randint(100, 5000)
        
        now_str = datetime.now().strftime("%H:%M:%S")
        self.history.append(self.price)
        self.timestamps.append(now_str)
        
        # Keep buffer limited
        if len(self.history) > 300:
            self.history = self.history[-300:]
            self.timestamps = self.timestamps[-300:]


class TrialWindow(tk.Toplevel):
    """Trial Mode: Replicates StockApp UI but uses simulated data."""
    
    SUMMARY_FIELDS = [
        "Open", "Day High", "Day Low", "Prev Close",
        "Volume", "52W High", "52W Low", "Market Cap"
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Trial Playground - Simulation Mode")
        self.geometry("1280x800")
        self.configure(bg=COLORS["bg"])
        self.transient(parent) # Keep window on top of parent
        
        # --- Simulation State ---
        self.tickers = {
            "SIM-ALPHA": SimulatedTicker("SIM-ALPHA", 150.00),
            "SIM-BETA": SimulatedTicker("SIM-BETA", 2450.50),
            "SIM-GAMMA": SimulatedTicker("SIM-GAMMA", 45.20),
            "SIM-DELTA": SimulatedTicker("SIM-DELTA", 12.80),
        }
        self.current_symbol = "SIM-ALPHA"
        self.sim_running = True
        self.sim_job = None

        # Portfolio State
        self.holdings = {t: 0 for t in self.tickers}
        self.transactions = []

        # UI Variables
        self.price_var = tk.StringVar(value="--")
        self.change_var = tk.StringVar(value="--")
        self.status_var = tk.StringVar(value="Market Open (Simulated)")
        self.summary_labels = {}
        
        # --- Layout ---
        self._build_layout()
        self._init_plot()
        
        # --- Start ---
        self._update_watchlist_ui()
        self._simulation_loop()

    def _build_layout(self):
        # Header
        header = tk.Frame(self, bg=COLORS["bg"], height=60)
        header.pack(fill=tk.X, padx=25, pady=20)
        
        tk.Label(header, text="TRIAL MODE", font=("Segoe UI", 14, "bold"), fg=COLORS["success"], bg=COLORS["bg"]).pack(side=tk.LEFT)
        
        controls = tk.Frame(header, bg=COLORS["bg"])
        controls.pack(side=tk.RIGHT)
        
        self.toggle_btn = ttk.Button(controls, text="Pause", command=self.toggle_simulation, width=8)
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Reset", command=self.reset_simulation, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="⬇ CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)

        # Main Container (Sidebar + Content)
        main_container = tk.Frame(self, bg=COLORS["bg"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

        # Sidebar
        sidebar = ttk.Frame(main_container, style="Card.TFrame", width=300)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        sidebar.pack_propagate(False)

        sb_header = tk.Frame(sidebar, bg=COLORS["surface"])
        sb_header.pack(fill=tk.X, padx=15, pady=15)
        tk.Label(sb_header, text="WATCHLIST (SIM)", font=("Segoe UI", 10, "bold"), fg=COLORS["text_muted"], bg=COLORS["surface"]).pack(side=tk.LEFT)

        tree_frame = tk.Frame(sidebar, bg=COLORS["surface"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.watchlist_tree = ttk.Treeview(tree_frame, columns=("ticker", "last", "change"), show="headings", selectmode="browse")
        self.watchlist_tree.heading("ticker", text="SYMBOL", anchor="w")
        self.watchlist_tree.heading("last", text="PRICE", anchor="e")
        self.watchlist_tree.heading("change", text="%", anchor="e")
        self.watchlist_tree.column("ticker", width=90)
        self.watchlist_tree.column("last", width=80, anchor="e")
        self.watchlist_tree.column("change", width=70, anchor="e")
        self.watchlist_tree.pack(fill=tk.BOTH, expand=True)
        self.watchlist_tree.tag_configure("gain", foreground=COLORS["success"])
        self.watchlist_tree.tag_configure("loss", foreground=COLORS["danger"])
        self.watchlist_tree.bind("<<TreeviewSelect>>", self._on_watchlist_select)

        # Content Area
        content = tk.Frame(main_container, bg=COLORS["bg"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Stats Card (Price + Buy/Sell)
        stats_card = ttk.Frame(content, style="Card.TFrame")
        stats_card.pack(fill=tk.X, pady=(0, 20))
        
        p_header = tk.Frame(stats_card, bg=COLORS["surface"])
        p_header.pack(fill=tk.X, padx=25, pady=20)
        
        # Price Display
        self.price_label = tk.Label(p_header, textvariable=self.price_var, font=("Segoe UI", 36, "bold"), bg=COLORS["surface"], fg=COLORS["text"])
        self.price_label.pack(side=tk.LEFT)
        self.change_label = tk.Label(p_header, textvariable=self.change_var, font=("Segoe UI", 18), bg=COLORS["surface"], fg=COLORS["text_muted"])
        self.change_label.pack(side=tk.LEFT, padx=(25, 0), pady=(12, 0))
        
        tk.Label(p_header, textvariable=self.status_var, font=("Segoe UI", 9), bg=COLORS["surface"], fg=COLORS["text_muted"]).pack(side=tk.RIGHT, pady=(15,0))

        trade_box = tk.Frame(p_header, bg=COLORS["surface"])
        trade_box.pack(side=tk.RIGHT, pady=(12, 0), padx=20)
        ttk.Button(trade_box, text="BUY", style="Accent.TButton", command=lambda: self._trade("BUY")).pack(side=tk.LEFT, padx=5)
        ttk.Button(trade_box, text="SELL", command=lambda: self._trade("SELL")).pack(side=tk.LEFT, padx=5)

        # Summary Grid
        grid_frame = tk.Frame(stats_card, bg=COLORS["surface"])
        grid_frame.pack(fill=tk.X, padx=25, pady=(0, 25))
        for idx, label in enumerate(self.SUMMARY_FIELDS):
            col, row = idx % 4, idx // 4
            f = tk.Frame(grid_frame, bg=COLORS["surface"])
            f.grid(row=row, column=col, sticky="ew", padx=10, pady=10)
            tk.Label(f, text=label.upper(), font=("Segoe UI", 8, "bold"), fg=COLORS["text_muted"], bg=COLORS["surface"]).pack(anchor="w")
            val_lbl = tk.Label(f, text="--", font=("Segoe UI", 12), fg=COLORS["text"], bg=COLORS["surface"])
            val_lbl.pack(anchor="w")
            self.summary_labels[label] = val_lbl
        for c in range(4): grid_frame.columnconfigure(c, weight=1)

        # Chart
        self.plot_container = ttk.Frame(content, style="Card.TFrame")
        self.plot_container.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Transactions / History (Bottom Panel)
        trans_card = ttk.Frame(content, style="Card.TFrame", height=200)
        trans_card.pack(fill=tk.X)
        trans_header = tk.Frame(trans_card, bg=COLORS["surface"])
        trans_header.pack(fill=tk.X, padx=15, pady=10)
        tk.Label(trans_header, text="YOUR TRANSACTIONS", font=("Segoe UI", 10, "bold"), fg=COLORS["text_muted"], bg=COLORS["surface"]).pack(side=tk.LEFT)
        
        self.tx_tree = ttk.Treeview(trans_card, columns=("date", "ticker", "side", "price", "qty", "total"), show="headings", height=6)
        headings = ["Time", "Ticker", "Side", "Price", "Qty", "Total"]
        for col, h in zip(self.tx_tree["columns"], headings):
            self.tx_tree.heading(col, text=h, anchor="w" if col in ["date", "ticker"] else "e")
            self.tx_tree.column(col, width=100, anchor="w" if col in ["date", "ticker"] else "e")
        self.tx_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _init_plot(self):
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.figure.patch.set_facecolor(COLORS["surface"])
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor(COLORS["surface"])
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.spines['bottom'].set_visible(True)
        self.ax.spines['bottom'].set_color(COLORS["border"])
        self.ax.spines['left'].set_visible(True)
        self.ax.spines['left'].set_color(COLORS["border"])
        self.ax.tick_params(axis='x', colors=COLORS["text_muted"], labelsize=9)
        self.ax.tick_params(axis='y', colors=COLORS["text_muted"], labelsize=9)
        self.ax.grid(True, color=COLORS["border"], linestyle='--', linewidth=0.5, alpha=0.4)
        self.line, = self.ax.plot([], [], color=COLORS["accent"], linewidth=2)
        self.fill_area = None
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    def _simulation_loop(self):
        if self.sim_running:
            # Update all simulated tickers
            for t in self.tickers.values():
                t.tick()
            
            # Refresh UI
            self._update_watchlist_ui()
            self._update_main_view()
            
            self.sim_job = self.after(1000, self._simulation_loop)

    def _update_watchlist_ui(self):
        # Save selection
        selected = self.watchlist_tree.selection()
        self.watchlist_tree.delete(*self.watchlist_tree.get_children())
        
        for symbol, data in self.tickers.items():
            price = data.price
            change = price - data.prev_close
            change_pct = (change / data.prev_close) * 100
            
            tag = "gain" if change >= 0 else "loss"
            sign = "+" if change >= 0 else ""
            
            self.watchlist_tree.insert(
                "", tk.END, iid=symbol, 
                values=(symbol, f"{price:,.2f}", f"{sign}{change_pct:.2f}%"),
                tags=(tag,)
            )
        
        # Restore selection or select default
        if selected and selected[0] in self.tickers:
            self.watchlist_tree.selection_set(selected[0])
        elif self.current_symbol in self.tickers:
            self.watchlist_tree.selection_set(self.current_symbol)

    def _on_watchlist_select(self, event):
        sel = self.watchlist_tree.selection()
        if not sel:
            return
        symbol = sel[0]
        if symbol != self.current_symbol:
            self.current_symbol = symbol
            self._update_main_view(force_redraw=True)

    def _update_main_view(self, force_redraw=False):
        if self.current_symbol not in self.tickers:
            return
        
        data = self.tickers[self.current_symbol]
        
        # 1. Update Price Header
        self.price_var.set(f"{data.price:,.2f}")
        change = data.price - data.prev_close
        change_pct = (change / data.prev_close) * 100
        sign = "+" if change >= 0 else "-"
        self.change_var.set(f"{sign}{abs(change):,.2f} ({sign}{abs(change_pct):.2f}%)")
        self.change_label.config(fg=COLORS["success"] if change >= 0 else COLORS["danger"])
        
        # 2. Update Summary Grid
        vals = {
            "Open": f"{data.open_price:,.2f}",
            "Day High": f"{data.day_high:,.2f}",
            "Day Low": f"{data.day_low:,.2f}",
            "Prev Close": f"{data.prev_close:,.2f}",
            "Volume": f"{data.volume:,}",
            "52W High": f"{data.day_high * 1.1:,.2f}", # Fake
            "52W Low": f"{data.day_low * 0.9:,.2f}",   # Fake
            "Market Cap": "--"
        }
        for label, val in vals.items():
            if label in self.summary_labels:
                self.summary_labels[label].config(text=val)

        # 3. Update Chart
        x_data = range(len(data.history))
        self.line.set_data(x_data, data.history)
        
        if self.fill_area:
            self.fill_area.remove()
            self.fill_area = None
            
        min_p = min(data.history)
        max_p = max(data.history)
        padding = (max_p - min_p) * 0.1 if max_p != min_p else min_p * 0.01
        base = min_p - padding
        
        self.fill_area = self.ax.fill_between(x_data, data.history, base, color=COLORS["accent"], alpha=0.1)
        
        # X Ticks
        if len(data.timestamps) > 0:
            step = max(1, len(data.timestamps) // 8)
            xticks = list(range(0, len(data.timestamps), step))
            self.ax.set_xticks(xticks)
            self.ax.set_xticklabels([data.timestamps[i] for i in xticks], rotation=0, fontsize=9)
            
        self.ax.set_ylim(min_p * 0.99, max_p * 1.01)
        self.ax.set_xlim(0, max(len(data.history)-1, 1))
        self.canvas.draw_idle()

    def _trade(self, side):
        ticker = self.current_symbol
        price = self.tickers[ticker].price
        owned = self.holdings.get(ticker, 0)
        
        qty = simpledialog.askinteger("Trial Trade", f"Enter quantity to {side} {ticker}:\n(Owned: {owned})", parent=self, minvalue=1)
        if not qty:
            return
            
        if side == "SELL" and qty > owned:
            messagebox.showerror("Error", "Insufficient holdings", parent=self)
            return
            
        # Execute
        total = price * qty
        if side == "BUY":
            self.holdings[ticker] = owned + qty
        else:
            self.holdings[ticker] = owned - qty
            
        # Log
        ts = datetime.now().strftime("%H:%M:%S")
        self.transactions.insert(0, {
            "date": ts, "ticker": ticker, "side": side,
            "price": price, "qty": qty, "total": total
        })
        
        # Update Table
        self.tx_tree.delete(*self.tx_tree.get_children())
        for t in self.transactions:
            self.tx_tree.insert("", tk.END, values=(
                t["date"], t["ticker"], t["side"],
                f"{t['price']:,.2f}", t["qty"], f"{t['total']:,.2f}"
            ))
            
        messagebox.showinfo("Success", f"{side} {qty} {ticker} completed.", parent=self)

    def toggle_simulation(self):
        self.sim_running = not self.sim_running
        if self.sim_running:
            self.toggle_btn.config(text="Pause")
            self._simulation_loop()
        else:
            self.toggle_btn.config(text="Resume")
            if self.sim_job:
                self.after_cancel(self.sim_job)
                self.sim_job = None

    def reset_simulation(self):
        # Reset prices to initial
        self.tickers = {
            "SIM-ALPHA": SimulatedTicker("SIM-ALPHA", 150.00),
            "SIM-BETA": SimulatedTicker("SIM-BETA", 2450.50),
            "SIM-GAMMA": SimulatedTicker("SIM-GAMMA", 45.20),
            "SIM-DELTA": SimulatedTicker("SIM-DELTA", 12.80),
        }
        self.holdings = {t: 0 for t in self.tickers}
        self.transactions = []
        self.tx_tree.delete(*self.tx_tree.get_children())
        self._update_watchlist_ui()
        self._update_main_view()

    def export_csv(self):
        if not self.transactions:
            return
        df = pd.DataFrame(self.transactions)
        fn = filedialog.asksaveasfilename(defaultextension=".csv", parent=self)
        if fn:
            df.to_csv(fn, index=False)
            messagebox.showinfo("Export", "Saved successfully.", parent=self)

if __name__ == "__main__":
    # 1. Initialize Supabase Client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 2. Setup Root for Login Dialog
    # We use a temporary root for the login screen to avoid having two main loops or hidden windows later
    root = tk.Tk()
    root.withdraw() # Hide root window

    # 3. Show Login
    login_window = LoginDialog(root, supabase)
    root.wait_window(login_window)

    # 4. Check results
    session = login_window.session
    
    # DESTROY the temporary root before creating the main app
    # This is crucial to avoid "multiple root" errors in Tkinter
    root.destroy()

    # 5. If Login Successful, Start App
    if session:
        app = StockApp(supabase, session)
        app.mainloop()
