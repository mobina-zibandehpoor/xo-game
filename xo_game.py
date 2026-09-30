"""XO (tic-tac-toe). The opponent learns a Q-value for every legal board. Python standard library only."""

import array
import random
import time
import tkinter as tk

try:
    from ctypes import windll

    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

N_STATES = 3**9
SWAP = (0, 2, 1)


def winning_line(board, index, player):
    r, c = divmod(index, 3)
    row = r * 3
    if board[row] == player and board[row + 1] == player and board[row + 2] == player:
        return (row, row + 1, row + 2)
    if board[c] == player and board[c + 3] == player and board[c + 6] == player:
        return (c, c + 3, c + 6)
    if r == c and board[0] == player and board[4] == player and board[8] == player:
        return (0, 4, 8)
    if r + c == 2 and board[2] == player and board[4] == player and board[6] == player:
        return (2, 4, 6)
    return None


def state_id(board, player):
    """Base-3 id from `player`'s view: 1 is the side to move, 2 is the opponent."""
    cells = board if player == 1 else [SWAP[value] for value in board]
    return (
        cells[0]
        + 3 * cells[1]
        + 9 * cells[2]
        + 27 * cells[3]
        + 81 * cells[4]
        + 243 * cells[5]
        + 729 * cells[6]
        + 2187 * cells[7]
        + 6561 * cells[8]
    )


class QAgent:
    """Optimal action values from the Q-learning backup.

    Each move adds a mark, so the game is a short acyclic graph. One sweep from
    full boards back to the empty board sets Q(s, a) to the true value:
    +1 win, 0 draw, -1 loss.
    """

    def __init__(self):
        self.q = array.array("f", [0.0]) * (N_STATES * 9)
        self.positions = 0
        self.seconds = 0.0

    def choose(self, board, player):
        legal = [i for i in range(9) if board[i] == 0]
        base = state_id(board, player) * 9
        best = max(self.q[base + index] for index in legal)
        picks = [index for index in legal if self.q[base + index] >= best - 1e-6]
        return random.choice(picks)

    def train(self):
        started = time.perf_counter()
        seen = set()
        layers = [[] for _ in range(10)]

        def visit(board):
            sid = state_id(board, 1)
            if sid in seen:
                return
            seen.add(sid)
            layers[9 - board.count(0)].append(board[:])
            for index in range(9):
                if board[index] != 0:
                    continue
                board[index] = 1
                if not winning_line(board, index, 1) and 0 in board:
                    visit([SWAP[value] for value in board])
                board[index] = 0

        visit([0] * 9)
        q = self.q
        for boards in reversed(layers):
            for board in boards:
                base = state_id(board, 1) * 9
                for index in range(9):
                    if board[index] != 0:
                        continue
                    board[index] = 1
                    if winning_line(board, index, 1):
                        target = 1.0
                    elif 0 not in board:
                        target = 0.0
                    else:
                        flipped = [SWAP[value] for value in board]
                        opp = state_id(flipped, 1) * 9
                        best = max(q[opp + move] for move in range(9) if flipped[move] == 0)
                        target = -best
                    q[base + index] = target
                    board[index] = 0
        self.positions = len(seen)
        self.seconds = time.perf_counter() - started


class XOApp(tk.Tk):
    BG = "#10141c"
    PANEL = "#181e2a"
    CELL = "#222a3a"
    CELL_HOVER = "#2c3650"
    X_COLOR = "#6cb6ff"
    O_COLOR = "#ff7d8a"
    WIN = "#3ecf8e"
    TEXT = "#edf2f7"
    MUTED = "#93a0b5"
    BUTTON = "#2f6fed"
    BUTTON_TEXT = "#f7f9fc"

    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.title("XO")
        self.configure(bg=self.BG)
        self.resizable(False, False)

        self.board = [0] * 9
        self.human = 1
        self.turn = 1
        self.over = False
        self.win_cells = ()
        self.hover = None
        self.scores = [0, 0, 0]  # you, ai, draw
        self.cell = 112
        self.gap = 10
        size = self.cell * 3 + self.gap * 2

        header = tk.Frame(self, bg=self.BG)
        header.pack(fill="x", padx=28, pady=(22, 0))
        tk.Label(
            header, text="XO", bg=self.BG, fg=self.TEXT,
            font=("Segoe UI", 28, "bold"),
        ).pack(anchor="w")
        self.train_label = tk.Label(
            header,
            text="Q-learning  ·  training...",
            bg=self.BG, fg=self.MUTED, font=("Segoe UI", 10),
        )
        self.train_label.pack(anchor="w", pady=(2, 0))

        scores = tk.Frame(self, bg=self.BG)
        scores.pack(fill="x", padx=28, pady=(16, 8))
        self.score_labels = []
        for title in ("You", "Draws", "AI"):
            box = tk.Frame(scores, bg=self.PANEL, padx=14, pady=8)
            box.pack(side="left", expand=True, fill="x", padx=4)
            tk.Label(box, text=title, bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9)).pack()
            label = tk.Label(box, text="0", bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 18, "bold"))
            label.pack()
            self.score_labels.append(label)

        board_wrap = tk.Frame(self, bg=self.BG)
        board_wrap.pack(padx=28, pady=8)
        self.canvas = tk.Canvas(
            board_wrap, width=size, height=size, bg=self.BG,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<Leave>", self.on_leave)

        self.status = tk.Label(
            self, text="Training...", bg=self.BG, fg=self.TEXT,
            font=("Segoe UI", 12),
        )
        self.status.pack(pady=(12, 4))

        controls = tk.Frame(self, bg=self.BG)
        controls.pack(pady=(8, 22))
        self._button(controls, "New game", self.new_game).pack(side="left", padx=6)
        self._button(controls, "Let AI start", self.ai_starts).pack(side="left", padx=6)

        self.draw()
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _button(self, parent, text, command):
        btn = tk.Button(
            parent, text=text, command=command,
            bg=self.BUTTON, fg=self.BUTTON_TEXT, activebackground="#4c86f5",
            activeforeground=self.BUTTON_TEXT, relief="flat", bd=0,
            padx=16, pady=8, font=("Segoe UI", 10, "bold"), cursor="hand2",
        )
        return btn

    def cell_box(self, index):
        r, c = divmod(index, 3)
        x0 = c * (self.cell + self.gap)
        y0 = r * (self.cell + self.gap)
        return x0, y0, x0 + self.cell, y0 + self.cell

    def cell_at(self, x, y):
        for i in range(9):
            x0, y0, x1, y1 = self.cell_box(i)
            if x0 <= x <= x1 and y0 <= y <= y1:
                return i
        return None

    def draw(self):
        self.canvas.delete("all")
        for i in range(9):
            x0, y0, x1, y1 = self.cell_box(i)
            won = i in self.win_cells
            hot = i == self.hover and not self.over and self.board[i] == 0 and self.turn == self.human
            fill = "#1c3d32" if won else (self.CELL_HOVER if hot else self.CELL)
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="", width=0)
            mark = self.board[i]
            if mark:
                self._draw_mark(i, mark, self.WIN if won else None)
        self.score_labels[0].configure(text=str(self.scores[0]))
        self.score_labels[1].configure(text=str(self.scores[1]))
        self.score_labels[2].configure(text=str(self.scores[2]))

    def _draw_mark(self, index, mark, color):
        x0, y0, x1, y1 = self.cell_box(index)
        pad = 30
        if mark == 1:
            ink = color or self.X_COLOR
            self.canvas.create_line(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=ink, width=8, capstyle="round")
            self.canvas.create_line(x0 + pad, y1 - pad, x1 - pad, y0 + pad, fill=ink, width=8, capstyle="round")
        else:
            ink = color or self.O_COLOR
            self.canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, outline=ink, width=8)

    def on_move(self, event):
        cell = self.cell_at(event.x, event.y)
        if cell != self.hover:
            self.hover = cell
            self.draw()

    def on_leave(self, _event):
        self.hover = None
        self.draw()

    def on_click(self, event):
        if self.agent.positions == 0 or self.over or self.turn != self.human:
            return
        cell = self.cell_at(event.x, event.y)
        if cell is None or self.board[cell] != 0:
            return
        self.place(cell, self.human)
        if not self.over:
            self.status.configure(text="AI's turn")
            self.after(60, self.ai_move)

    def place(self, index, player):
        self.board[index] = player
        line = winning_line(self.board, index, player)
        if line:
            self.over = True
            self.win_cells = line
            if player == self.human:
                self.scores[0] += 1
                self.status.configure(text="You win")
            else:
                self.scores[2] += 1
                self.status.configure(text="AI wins")
        elif all(self.board):
            self.over = True
            self.scores[1] += 1
            self.status.configure(text="Draw")
        else:
            self.turn = 3 - player
            if self.turn == self.human:
                mark = "X" if self.human == 1 else "O"
                self.status.configure(text=f"Your turn  ·  you are {mark}")
        self.draw()

    def ai_move(self):
        if self.over or self.turn == self.human:
            return
        move = self.agent.choose(self.board, self.turn)
        self.place(move, self.turn)

    def new_game(self, human=1):
        self.board = [0] * 9
        self.human = human
        self.turn = 1
        self.over = False
        self.win_cells = ()
        mark = "X" if human == 1 else "O"
        if human == 1:
            self.status.configure(text=f"Your turn  ·  you are {mark}")
            self.draw()
        else:
            self.status.configure(text="AI's turn  ·  you are O")
            self.draw()
            self.after(180, self.ai_move)

    def ai_starts(self):
        self.new_game(human=2)


def main():
    agent = QAgent()
    app = XOApp(agent)
    app.update()
    agent.train()
    app.train_label.configure(
        text=f"Q-learning  ·  {agent.positions:,} positions in {agent.seconds:.2f}s"
    )
    app.status.configure(text="Your turn  ·  you are X")
    app.mainloop()


if __name__ == "__main__":
    main()
