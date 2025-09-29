import tkinter as tk
import multiprocessing as mp
from app import SystemStressApp


if __name__ == "__main__":
    mp.set_start_method("spawn")  
    root = tk.Tk()
    app = SystemStressApp(root)
    root.mainloop()
