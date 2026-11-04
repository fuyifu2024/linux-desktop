#!/usr/bin/python3
"""Per-user onboarding and reversible layout reset; no privileged operations."""
import argparse
import os
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import messagebox

LANGUAGES={'简体中文':'zh-Hans','繁體中文':'zh-Hant','English':'en','日本語':'ja','Русский':'ru','Français':'fr','Español':'es'}
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--autostart',action='store_true'); parser.add_argument('--reset-layout',action='store_true')
    args=parser.parse_args()
    marker=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'linux-desktop/welcome-seen'
    if args.autostart and marker.exists(): return
    window=tk.Tk(); window.title('Welcome · linux-desktop'); window.geometry('600x360')
    def invoke(fn):
        try: fn()
        except Exception as exc: messagebox.showerror('Error',str(exc))
    def reset():
        if not messagebox.askyesno('Reset desktop layout?', 'Reset the taskbar settings and window buttons?'): return
        for cmd in [ ['gsettings','reset-recursively','org.gnome.shell.extensions.dash-to-panel'],
                     ['gsettings','reset','org.gnome.desktop.wm.preferences','button-layout'] ]:
            subprocess.run(cmd,check=True)
    if args.reset_layout:
        invoke(reset); window.destroy(); return
    tk.Label(window,text='Welcome · 欢迎 · ようこそ',font=('',20)).pack(pady=18)
    choice=tk.StringVar(value='English')
    tk.OptionMenu(window,choice,*LANGUAGES).pack()
    def tutorial():
        subprocess.Popen(['xdg-open',(Path('/usr/share/linux-desktop/tutorial')/(LANGUAGES[choice.get()]+'.html')).as_uri()])
    tk.Button(window,text='Open offline tutorial / 打开离线教程',command=lambda:invoke(tutorial)).pack(pady=10)
    tk.Button(window,text='System language & keyboard',command=lambda:invoke(lambda:subprocess.Popen(['gnome-control-center','region']))).pack(pady=5)
    def defaults():
        if not messagebox.askyesno('Windows installers', 'Open Windows installer files with this application manager by default?'): return
        for mime in ['application/x-ms-dos-executable','application/x-msdownload','application/x-msi','application/vnd.microsoft.portable-executable']:
            subprocess.run(['xdg-mime','default','linux-desktop-winapps.desktop',mime],check=True)
    tk.Button(window,text='Set Windows installer file associations',command=lambda:invoke(defaults)).pack(pady=5)
    tk.Button(window,text='Reset taskbar layout',command=lambda:invoke(reset)).pack(pady=5)
    def finish():
        marker.parent.mkdir(parents=True,exist_ok=True); marker.write_text('1\n'); window.destroy()
    tk.Button(window,text='Finish / 完成',command=lambda:invoke(finish)).pack(pady=10)
    window.mainloop()
if __name__=='__main__': main()
