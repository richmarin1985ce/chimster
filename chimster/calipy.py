"""Calipy: a deliberately non-AI, local, optional office-assistant parody."""
import math
import tkinter as tk

TIPS = {
    "Project": ("It looks like you're starting a mod. Want to set up a project first?", "A tidy project is a measurable improvement."),
    "Worldspace browser": ("It looks like you're exploring a worldspace. Check the selected cell before editing.", "I can measure distances, not your ambition."),
    "Navmesh editor": ("It looks like you're making somewhere to walk. Review generated navigation before finalizing.", "Even I have trouble finding the shortest path."),
    "Script editor": ("It looks like you're writing a script. Select the correct game and compiler before compiling.", "Have you tried measuring twice and compiling once?"),
    "Native records": ("It looks like you're editing records. Check the target plugin and record identity.", "I'm a caliper, not a load-order manager."),
    "Quest editor": ("It looks like you're making a quest. Check stages and conditions before exporting.", "I have a quest for you: finish your quest."),
    "3D viewport": ("It looks like you're working in 3D. Check your selection before transforming it.", "Finally, something with dimensions."),
    "Texture Forge": ("It looks like you're preparing textures. Check the target format and dimensions.", "Pixels are just very small things to measure."),
    "Local wiki": ("It looks like you're reading the manual. Excellent. My work here is done.", "I promise not to measure the length of every article."),
}
GENERAL = ("It looks like you're making a mod. Measure twice, save often.",
           "I'm Calipy. I have absolutely no artificial intelligence.",
           "Need actual help? Try Help > Local wiki.",
           "I have two jaws and zero useful opinions.")


def tip_for(tab, index=0):
    lines = TIPS.get(tab, GENERAL)
    return lines[index % len(lines)]


def clamp_position(x, y, width, height, overlay_width, overlay_height):
    return (max(0, min(x, max(0, width-overlay_width))),
            max(0, min(y, max(0, height-overlay_height))))


class Calipy:
    """A child overlay, never a global or always-on-top desktop window."""
    def __init__(self, root, tabs, menu):
        self.root, self.tabs = root, tabs
        self.enabled = tk.BooleanVar(master=root, value=False)
        self.frame = tk.Frame(root, bg="#313942", bd=0)
        self.bubble = tk.Frame(self.frame, bg="#fff7ce", bd=1, relief="solid")
        self.message = tk.Label(self.bubble, bg="#fff7ce", fg="#171717",
                                wraplength=196, justify="left", padx=6, pady=5)
        self.message.pack(fill="x")
        controls = tk.Frame(self.bubble, bg="#fff7ce")
        controls.pack(fill="x")
        tk.Button(controls, text="Another tip", command=self.next_tip,
                  relief="flat", bg="#fff7ce", takefocus=True).pack(side="left")
        tk.Button(controls, text="Dismiss", command=self.dismiss,
                  relief="flat", bg="#fff7ce", takefocus=True).pack(side="right")
        self.canvas = tk.Canvas(self.frame, width=112, height=132,
                                bg="#313942", highlightthickness=0,
                                cursor="hand2", takefocus=True)
        self.canvas.pack()
        self.popup = tk.Menu(self.canvas, tearoff=False)
        self.popup.add_command(label="Talk", command=self.next_tip)
        self.popup.add_command(label="Hide Calipy", command=self.hide)
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        self.canvas.bind("<Button-3>", self.context_menu)
        self.canvas.bind("<Return>", lambda _: self.next_tip())
        self.canvas.bind("<space>", lambda _: self.next_tip())
        menu.add_checkbutton(label="Activate Clippy (Calipy)", variable=self.enabled,
                             command=self.toggle)
        root.bind("<Configure>", self.resized, add="+")
        tabs.bind("<<NotebookTabChanged>>", self.tab_changed, add="+")
        self.x = self.y = 0
        self.positioned = False
        self.anchor = None
        self.moved = False
        self.timer = self.speech_timer = None
        self.tick = self.index = 0
        self.talking = False
        self.frame.bind("<Configure>", lambda _: self.place(), add="+")
        self.draw()

    def context_menu(self, event):
        try:
            self.popup.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup.grab_release()

    def current_tab(self):
        selection = self.tabs.select()
        return self.tabs.tab(selection, "text") if selection else ""

    def toggle(self):
        if self.enabled.get():
            self.show()
        else:
            self.hide()

    def show(self):
        if self.timer is not None:
            return
        self.enabled.set(True)
        if not self.positioned:
            self.x = self.root.winfo_width() - 250
            self.y = self.root.winfo_height() - 245
            self.positioned = True
        self.say("Hi! I'm Calipy. It looks like you're making a mod.")
        self.animate()

    def hide(self):
        self.enabled.set(False)
        for name in ("timer", "speech_timer"):
            job = getattr(self, name)
            if job is not None:
                self.root.after_cancel(job)
                setattr(self, name, None)
        self.talking = False
        self.anchor = None
        self.bubble.pack_forget()
        self.frame.place_forget()

    def place(self):
        if not self.enabled.get():
            return
        self.x, self.y = clamp_position(
            self.x, self.y, self.root.winfo_width(), self.root.winfo_height(),
            self.frame.winfo_reqwidth(), self.frame.winfo_reqheight())
        self.frame.place(x=self.x, y=self.y)
        self.frame.lift()

    def resized(self, event):
        if event.widget is self.root and self.enabled.get():
            self.place()

    def press(self, event):
        self.anchor = (event.x_root, event.y_root, self.x, self.y)
        self.moved = False

    def drag(self, event):
        if self.anchor is None:
            return
        sx, sy, x, y = self.anchor
        dx, dy = event.x_root-sx, event.y_root-sy
        if abs(dx)+abs(dy) >= 4:
            self.moved = True
        if self.moved:
            self.x, self.y = x+dx, y+dy
            self.place()

    def release(self, event):
        if self.anchor is not None and not self.moved:
            self.next_tip()
        self.anchor = None

    def tab_changed(self, _event):
        if self.enabled.get():
            self.index = 0
            self.say(tip_for(self.current_tab()))

    def next_tip(self):
        if self.enabled.get():
            self.index += 1
            self.say(tip_for(self.current_tab(), self.index))

    def say(self, line):
        if not self.enabled.get():
            return
        if self.speech_timer is not None:
            self.root.after_cancel(self.speech_timer)
        self.message.configure(text=line)
        self.bubble.pack(before=self.canvas, fill="x")
        self.talking = True
        self.place()
        self.speech_timer = self.root.after(9000, self.dismiss)

    def dismiss(self):
        if self.speech_timer is not None:
            self.root.after_cancel(self.speech_timer)
            self.speech_timer = None
        self.talking = False
        self.bubble.pack_forget()
        self.place()

    def animate(self):
        if not self.enabled.get():
            self.timer = None
            return
        self.tick += 1
        self.draw()
        self.timer = self.root.after(120, self.animate)

    def draw(self):
        c = self.canvas
        c.delete("all")
        phase = self.tick
        bob = round(3*math.sin(phase/4))
        slide = round(4*math.sin(phase/5)) if self.talking else 0
        # Original metallic vernier-caliper silhouette: fixed and sliding jaws.
        def line(coords, color, width):
            pts = [v+(bob if i%2 else 0) for i,v in enumerate(coords)]
            c.create_line(*pts, fill=color, width=width, capstyle="round",
                          joinstyle="round")
        c.create_oval(22, 119, 91, 129, fill="#222830", outline="")
        for color,width in (("#474d57",13),("#b4bdc7",9),("#edf2f5",3)):
            line([40,16,40,107,75,107],color,width)
            line([40,16,78,16,78,30],color,width)
            line([40,78+slide,78,78+slide,78,65+slide],color,width)
        c.create_rectangle(30,42+bob+slide,55,70+bob+slide,
                           fill="#aeb8c3",outline="#505965",width=2)
        for y in range(84,104,5):
            line([36,y,43,y],"#535d69",1)
        c.create_oval(46,44+bob+slide,52,50+bob+slide,
                      fill="#687381",outline="#3b424d")
        blink = phase % 43 in (40,41)
        for x in (52,73):
            if blink:
                line([x-8,37,x+8,37],"#181c20",3)
            else:
                c.create_oval(x-10,23+bob,x+10,48+bob,
                              fill="white",outline="#242a30",width=2)
                pupil = round(2*math.sin(phase/7))
                c.create_oval(x-3+pupil,33+bob,x+4+pupil,43+bob,
                              fill="#17191d",outline="")
            line([x-8,19,x+7,17],"#22262b",3)
        if self.talking and phase%4<2:
            c.create_oval(57,52+bob,70,61+bob,fill="#25272a",outline="")
        else:
            c.create_arc(55,46+bob,73,61+bob,start=205,extent=130,
                         style="arc",outline="#25272a",width=2)
