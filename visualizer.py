import pygame
import sys
import os
import numpy as np
from grid import MalwareGrid, S, I, R, P

# Layout constants
BG        = (15,  15,  20)
PANEL_COL = (22,  22,  30)
CELL      = 8
PADDING   = 10
GRID_ROWS = 80
GRID_COLS = 80
PANEL_W   = 320
STATUS_H  = 36

DEFAULT_COLORS = {
    S: (40,  80,  160),
    I: (210, 40,  40),
    R: (40,  160, 80),
    P: (220, 180, 40),
}

DIVIDER    = (40,  40,  55)
TEXT_DIM   = (90,  90, 110)
TEXT_MED   = (150, 150, 170)
TEXT_LIGHT = (200, 200, 215)
TEXT_WHITE = (220, 220, 230)

# Tiny drawing helpers

def draw_wrapped(surface, text, font, color, x, y, max_w, max_h=None):
    """Word-wrap text. Returns final y. Truncates with '…' if max_h given."""
    words  = text.split()
    line   = ""
    line_y = y
    lh     = font.get_height() + 2
    lines_out = []

    for word in words:
        test = line + word + " "
        if font.size(test)[0] > max_w and line:
            lines_out.append(line.strip())
            line = word + " "
        else:
            line = test
    if line:
        lines_out.append(line.strip())

    for i, ln in enumerate(lines_out):
        if max_h and (line_y + lh - y) > max_h:
            # truncate last visible line with ellipsis
            trunc = lines_out[i - 1] if i > 0 else ln
            while font.size(trunc + "…")[0] > max_w and trunc:
                trunc = trunc[:-1]
            surface.blit(font.render(trunc + "…", True, color), (x, line_y - lh))
            return line_y
        surface.blit(font.render(ln, True, color), (x, line_y))
        line_y += lh

    return line_y


def draw_divider(surface, x, y, w):
    pygame.draw.line(surface, DIVIDER, (x, y), (x + w, y))


def draw_section_label(surface, text, font, x, y, w):
    """Small all-caps section header with a trailing rule."""
    lbl  = font.render(text, True, TEXT_DIM)
    lw   = lbl.get_width()
    surface.blit(lbl, (x, y))
    pygame.draw.line(surface, DIVIDER, (x + lw + 6, y + 5), (x + w, y + 5))
    return y + font.get_height() + 4


# Slider widget (pure pygame, no pygame_gui dependency for sliders)

class Slider:
    """
    A clean horizontal slider drawn entirely in pygame.
    Clicking anywhere on the track sets the value immediately.
    """
    H      = 4    # track height
    THUMB  = 11   # thumb radius
    LH     = 32   # total row height reserved

    def __init__(self, label, min_val, max_val, default, fmt="{:.2f}"):
        self.label    = label
        self.min      = min_val
        self.max      = max_val
        self.value    = default
        self.fmt      = fmt
        self.rect     = pygame.Rect(0, 0, 1, 1)   # set in layout()
        self.dragging = False

    def layout(self, x, y, w):
        self.rect = pygame.Rect(x, y, w, self.LH)

    def draw(self, surface, font_sm):
        x, y, w = self.rect.x, self.rect.y, self.rect.w
        # Label left, value right
        val_str = self.fmt.format(self.value)
        lbl_surf = font_sm.render(self.label, True, TEXT_MED)
        val_surf = font_sm.render(val_str,   True, TEXT_LIGHT)
        surface.blit(lbl_surf, (x, y))
        surface.blit(val_surf, (x + w - val_surf.get_width(), y))

        # Track
        ty = y + self.LH - 14
        pygame.draw.rect(surface, (50, 50, 65), (x, ty - self.H // 2, w, self.H), border_radius=2)

        # Fill
        frac = (self.value - self.min) / (self.max - self.min)
        fw   = int(frac * w)
        if fw > 0:
            pygame.draw.rect(surface, (80, 120, 200), (x, ty - self.H // 2, fw, self.H), border_radius=2)

        # Thumb
        tx = x + fw
        pygame.draw.circle(surface, (160, 180, 230), (tx, ty), self.THUMB)
        pygame.draw.circle(surface, (80, 100, 160),  (tx, ty), self.THUMB, 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._in_track(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        return False

    def _in_track(self, pos):
        x, y, w = self.rect.x, self.rect.y, self.rect.w
        ty = y + self.LH - 14
        hit_x = x - self.THUMB <= pos[0] <= x + w + self.THUMB
        hit_y = ty - self.THUMB - 2 <= pos[1] <= ty + self.THUMB + 2
        return hit_x and hit_y

    def _set_from_x(self, mx):
        frac       = (mx - self.rect.x) / self.rect.w
        frac       = max(0.0, min(1.0, frac))
        self.value = self.min + frac * (self.max - self.min)

    def set_value(self, v):
        self.value = max(self.min, min(self.max, v))


# Button helper

class Button:
    def __init__(self, label, accent=(60, 100, 180)):
        self.label  = label
        self.accent = accent
        self.rect   = pygame.Rect(0, 0, 1, 1)
        self._hover = False

    def layout(self, x, y, w, h=22):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, surface, font):
        col = tuple(min(255, c + 30) for c in self.accent) if self._hover else self.accent
        pygame.draw.rect(surface, col,       self.rect, border_radius=4)
        pygame.draw.rect(surface, DIVIDER,   self.rect, 1, border_radius=4)
        lbl = font.render(self.label, True, TEXT_WHITE)
        lx  = self.rect.x + (self.rect.w - lbl.get_width())  // 2
        ly  = self.rect.y + (self.rect.h - lbl.get_height()) // 2
        surface.blit(lbl, (lx, ly))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False


# Topology selector (cycle through options on click)

TOPOLOGIES = ["Grid", "Random", "Hub-and-spoke"]

class TopoCycler:
    def __init__(self):
        self.index = 0
        self.rect  = pygame.Rect(0, 0, 1, 1)
        self._hover = False

    @property
    def value(self):
        return TOPOLOGIES[self.index]

    def set_value(self, v):
        if v in TOPOLOGIES:
            self.index = TOPOLOGIES.index(v)

    def layout(self, x, y, w, h=22):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, surface, font_sm):
        x, y, w, h = self.rect
        pygame.draw.rect(surface, (35, 35, 48), self.rect, border_radius=4)
        pygame.draw.rect(surface, DIVIDER,      self.rect, 1, border_radius=4)

        lbl   = font_sm.render("Topology", True, TEXT_MED)
        val   = font_sm.render(f"< {self.value} >", True, TEXT_LIGHT)
        surface.blit(lbl, (x + 6, y + (h - lbl.get_height()) // 2))
        surface.blit(val, (x + w - val.get_width() - 6, y + (h - val.get_height()) // 2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.index = (self.index + 1) % len(TOPOLOGIES)
                return True
        return False


# Panel layout

def layout_panel(px, pw):
    """
    Returns a dict of pre-laid-out widgets given panel x-origin and width.
    Call once after window creation.
    """
    x  = px + 12
    w  = pw - 24
    y  = 0    # filled in during layout pass below

    sl_infect  = Slider("Infect rate",  0.01, 1.0,  0.30)
    sl_recover = Slider("Recover rate", 0.00, 0.50, 0.05)
    sl_patch   = Slider("Patch rate",   0.00, 0.20, 0.00)
    sl_speed   = Slider("Sim speed",    1,    60,   15,   fmt="{:.0f} fps")
    topo       = TopoCycler()
    btn_start  = Button(">> Start / Reset",  accent=(45, 95, 165))
    btn_load   = Button("[ ] Load Profile",   accent=(40, 80,  50))
    btn_export = Button("[E] Export CSV",      accent=(70, 55, 100))

    widgets = dict(
        sl_infect  = sl_infect,
        sl_recover = sl_recover,
        sl_patch   = sl_patch,
        sl_speed   = sl_speed,
        topo       = topo,
        btn_start  = btn_start,
        btn_load   = btn_load,
        btn_export = btn_export,
    )
    return widgets, x, w


# Grid factories

def make_grid_from_sliders(widgets):
    return MalwareGrid(
        rows        = GRID_ROWS,
        cols        = GRID_COLS,
        infect_rate = widgets["sl_infect"].value,
        recover_rate= widgets["sl_recover"].value,
        patch_rate  = widgets["sl_patch"].value,
        topology    = widgets["topo"].value,
    )


def load_profile_grid(path, widgets):
    """Load profile and sync sliders to profile values."""
    grid = MalwareGrid.from_profile(path, rows=GRID_ROWS, cols=GRID_COLS)
    grid.seed_patient_zero()
    p = grid.profile
    widgets["sl_infect"].set_value(p["infect_rate"])
    widgets["sl_recover"].set_value(p["recover_rate"])
    widgets["sl_patch"].set_value(p["patch_rate"])
    widgets["topo"].set_value(p.get("topology", "Grid"))
    return grid


# Sparkline

def draw_sparkline(surface, history, color, x, y, w, h):
    """Draw the epidemic curve. Labels are handled by the caller."""
    if len(history) < 2:
        return
    pygame.draw.rect(surface, (25, 25, 35), (x, y, w, h), border_radius=3)
    pts  = [snap["I"] for snap in history[-w:]]
    peak = max(pts) if max(pts) > 0 else 1
    coords = [
        (x + i, y + h - int(v / peak * (h - 4)) - 2)
        for i, v in enumerate(pts)
    ]
    pygame.draw.lines(surface, color, False, coords, 1)
    return peak


# Prompt helpers

def prompt_profile_file():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title      = "Select threat / disease profile",
        initialdir = os.path.join(os.getcwd(), "profiles"),
        filetypes  = [("JSON profiles", "*.json")],
    )
    root.destroy()
    return path if path else None


def export_csv(history, grid, profile):
    import csv
    name     = profile["name"].replace(" ", "_") if profile else "custom"
    filename = f"export_{name}_tick{grid.tick}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        # Metadata block so the CSV is self-documenting
        if profile:
            writer.writerow([f"# Profile: {profile['name']}"])
            writer.writerow([f"# Domain:  {profile.get('domain', 'N/A')}"])
            writer.writerow([f"# Year:    {profile.get('year', 'N/A')}"])
            writer.writerow([f"# Source:  {profile.get('source', 'N/A')}"])
            writer.writerow([f"# infect_rate={profile['infect_rate']}  "
                             f"recover_rate={profile['recover_rate']}  "
                             f"patch_rate={profile['patch_rate']}  "
                             f"topology={profile['topology']}"])
            writer.writerow([])
        writer.writerow(["tick", "susceptible", "infected", "recovered", "patched", "total"])
        total = grid.rows * grid.cols
        for i, snap in enumerate(history):
            writer.writerow([
                i + 1,
                snap["S"],
                snap["I"],
                snap["R"],
                snap["P"],
                total,
            ])
    print(f"[export] {filename}")


# Main loop

def run():
    pygame.init()

    GRID_PX_W = GRID_COLS * CELL + PADDING * 2
    GRID_PX_H = GRID_ROWS * CELL + PADDING * 2
    W         = GRID_PX_W + PANEL_W
    H         = GRID_PX_H + STATUS_H

    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Contagion Dynamics Simulator")
    clock  = pygame.time.Clock()

    font      = pygame.font.SysFont("monospace", 13)
    font_sm   = pygame.font.SysFont("monospace", 12)
    font_bold = pygame.font.SysFont("monospace", 13, bold=True)

    # Build panel
    widgets, px, pw = layout_panel(GRID_PX_W, PANEL_W)

    # Initial simulation state
    grid           = make_grid_from_sliders(widgets)
    grid.seed_patient_zero()
    active_profile = None
    infect_color   = DEFAULT_COLORS[I]
    history        = []
    paused         = False
    fps_target     = 15

    def do_layout(panel_top=0):
        """Assign .rect to each widget. Returns y after last widget."""
        y = panel_top + 8
        # buttons at top
        bw = (pw - 4) // 2
        widgets["btn_load"].layout(px, y, bw, 26)
        widgets["btn_export"].layout(px + bw + 4, y, pw - bw - 4, 26)
        y += 32

        draw_divider(screen, px, y, pw)
        y += 8

        # sliders
        for key in ("sl_infect", "sl_recover", "sl_patch", "sl_speed"):
            widgets[key].layout(px, y, pw)
            y += Slider.LH + 8

        y += 2
        widgets["topo"].layout(px, y, pw, 24)
        y += 32

        draw_divider(screen, px, y, pw)
        y += 8

        widgets["btn_start"].layout(px, y, pw, 26)
        y += 32

        return y

    while True:
        td = clock.tick(fps_target) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Keyboard shortcuts
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_r:
                    # R = reset keeping current profile/sliders
                    if active_profile:
                        grid = MalwareGrid.from_profile_dict(active_profile,
                                                              GRID_ROWS, GRID_COLS)
                        grid.seed_patient_zero()
                    else:
                        grid = make_grid_from_sliders(widgets)
                        grid.seed_patient_zero()
                    history.clear()
                if event.key == pygame.K_e:
                    export_csv(history, grid, active_profile)

            # Click-to-infect on grid
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if mx < GRID_PX_W and my < GRID_PX_H:
                    c = (mx - PADDING) // CELL
                    r = (my - PADDING) // CELL
                    if 0 <= r < grid.rows and 0 <= c < grid.cols:
                        grid.seed_patient_zero(row=r, col=c)

            # Widget events
            for key, w in widgets.items():
                if not w.handle_event(event):
                    continue

                # Sliders — apply live so tweaks show up without a reset
                if key == "sl_speed":
                    fps_target = max(1, int(widgets["sl_speed"].value))
                elif key in ("sl_infect", "sl_recover", "sl_patch"):
                    grid.infect_rate  = widgets["sl_infect"].value
                    grid.recover_rate = widgets["sl_recover"].value
                    grid.patch_rate   = widgets["sl_patch"].value

                # Start / Reset
                elif key == "btn_start":
                    if active_profile:
                        grid = MalwareGrid(
                            rows         = GRID_ROWS,
                            cols         = GRID_COLS,
                            infect_rate  = widgets["sl_infect"].value,
                            recover_rate = widgets["sl_recover"].value,
                            patch_rate   = widgets["sl_patch"].value,
                            topology     = widgets["topo"].value,
                            reinfection  = active_profile.get("reinfection", False),
                        )
                        grid.profile = active_profile
                    else:
                        grid = make_grid_from_sliders(widgets)
                    grid.seed_patient_zero()
                    history.clear()
                    paused = False

                # Load profile
                elif key == "btn_load":
                    profile_path = prompt_profile_file()
                    if profile_path:
                        grid           = load_profile_grid(profile_path, widgets)
                        active_profile = grid.profile
                        infect_color   = tuple(active_profile["color"])
                        history.clear()
                        paused = False

                # Export CSV
                elif key == "btn_export":
                    export_csv(history, grid, active_profile)

                break  # one widget per event

        # Simulation step
        if not paused:
            grid.step()
            history.append(grid.counts())

        # Draw
        screen.fill(BG)

        # Grid cells
        colors = {S: DEFAULT_COLORS[S], I: infect_color,
                  R: DEFAULT_COLORS[R], P: DEFAULT_COLORS[P]}
        for r in range(grid.rows):
            for c in range(grid.cols):
                col = colors[grid.grid[r, c]]
                pygame.draw.rect(screen, col,
                    (PADDING + c * CELL, PADDING + r * CELL, CELL - 1, CELL - 1))

        # Panel background
        pygame.draw.rect(screen, PANEL_COL, (GRID_PX_W, 0, PANEL_W, H))

        # Layout & draw widgets (top of panel) 
        widget_bottom = do_layout(panel_top=0)

        for w in widgets.values():
            w.draw(screen, font_sm)

        # Profile info block (below widgets) 
        info_y = widget_bottom + 4
        draw_divider(screen, px, info_y, pw)
        info_y += 6

        if active_profile:
            domain_color = (120, 200, 255) if active_profile["domain"] == "cybersecurity" \
                           else (255, 160, 80)
            screen.blit(font_bold.render(active_profile["domain"].upper(), True, domain_color),
                        (px, info_y))
            info_y += 17
            screen.blit(font_bold.render(active_profile["name"], True, TEXT_WHITE),
                        (px, info_y))
            info_y += 17
            year = active_profile.get("year", "")
            src  = active_profile.get("source", "")
            meta = f"{year}  {src}" if src else str(year)
            screen.blit(font_sm.render(meta, True, TEXT_DIM), (px, info_y))
            info_y += 16
            draw_divider(screen, px, info_y, pw)
            info_y += 5
            info_y = draw_wrapped(screen, active_profile.get("description", ""),
                                  font_sm, TEXT_MED, px, info_y, pw, max_h=68)
            draw_divider(screen, px, info_y + 2, pw)
            info_y += 10

        # Stats
        counts = grid.counts()
        total  = grid.rows * grid.cols
        info_y = draw_section_label(screen, "COUNTS", font_sm, px, info_y, pw)
        for label, key, col in [
            ("Susceptible", "S", (80,  120, 200)),
            ("Infected",    "I", infect_color),
            ("Recovered",   "R", (60,  180, 100)),
            ("Patched",     "P", (200, 160, 40)),
        ]:
            pct = counts[key] / total * 100
            txt = font_sm.render(f"{label:<12} {counts[key]:>5}  {pct:5.1f}%", True, col)
            screen.blit(txt, (px, info_y))
            info_y += 17

        info_y += 8

        # Sparkline
        spark_h     = 60
        label_h     = font_sm.get_height()
        spark_top   = H - STATUS_H - spark_h - label_h - 24
        # Section label: "INFECTED OVER TIME" flush left, peak/tick flush right
        peak_val    = max(s["I"] for s in history) if history else 0
        right_lbl   = font_sm.render(f"peak {peak_val}  t={grid.tick}", True, TEXT_DIM)
        draw_section_label(screen, "INFECTED OVER TIME", font_sm, px, spark_top, pw)
        screen.blit(right_lbl, (px + pw - right_lbl.get_width(), spark_top))
        spark_y     = spark_top + label_h + 4
        draw_sparkline(screen, history, infect_color, px, spark_y, pw, spark_h)

        # Status bar
        state_str = "PAUSED — SPACE to resume" if paused else "RUNNING"
        pct_i     = counts["I"] / total * 100
        status    = (f"  Tick {grid.tick:04d}  │  "
                     f"Infected {counts['I']} ({pct_i:.1f}%)  │  "
                     f"{state_str}  │  "
                     f"[SPACE] pause  [R] reset  [E] export  [click] infect")
        pygame.draw.rect(screen, (10, 10, 14), (0, GRID_PX_H, W, STATUS_H))
        pygame.draw.line(screen, DIVIDER, (0, GRID_PX_H), (W, GRID_PX_H))
        screen.blit(font.render(status, True, TEXT_DIM), (0, GRID_PX_H + 10))

        pygame.display.flip()

def _from_profile_dict(cls, p, rows, cols):
    inst = cls(
        rows         = rows,
        cols         = cols,
        infect_rate  = p["infect_rate"],
        recover_rate = p["recover_rate"],
        patch_rate   = p["patch_rate"],
        topology     = p["topology"],
        reinfection  = p.get("reinfection", False),
    )
    inst.profile = p
    return inst

MalwareGrid.from_profile_dict = classmethod(lambda cls, p, r, c: _from_profile_dict(cls, p, r, c))


if __name__ == "__main__":
    run()