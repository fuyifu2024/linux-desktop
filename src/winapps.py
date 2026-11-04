#!/usr/bin/python3
"""Desktop Windows application manager. No shell invocation or host installation."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import uuid


def state_root():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share'))) / 'linux-desktop/winapps'


def app_dir(app_id):
    # Never accept arbitrary paths for a bottle identifier.
    if str(uuid.UUID(app_id)) != app_id:
        raise ValueError('Invalid application ID')
    return state_root()/app_id


def runtime():
    arch = platform.machine()
    config = Path('/etc/linux-desktop/runtimes.json')
    defaults = {'x86_64': '/usr/bin/wine', 'aarch64': '/usr/lib/hangover/wine'}
    paths = json.loads(config.read_text()) if config.exists() else defaults
    path = paths.get(arch, '')
    if not path.startswith('/') or not os.access(path, os.X_OK):
        raise RuntimeError(f'Windows runtime unavailable for {arch}. See Help → Windows applications.')
    return path


def validate_binary(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in ('.exe', '.msi'):
        raise ValueError('Select an .exe or .msi file')
    return path


def create_app(installer):
    installer = validate_binary(installer)
    app_id = str(uuid.uuid4())
    root = app_dir(app_id)
    root.mkdir(parents=True, mode=0o700)
    with installer.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    record = {'id': app_id, 'name': installer.stem, 'installer_sha256': digest,
              'status': 'created', 'executable': None}
    save(root, record)
    return app_id


def save(root, record):
    tmp = root/'app.json.tmp'
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    tmp.replace(root/'app.json')


def execute(app_id, binary, install=False, remove=False):
    binary = validate_binary(binary) if binary else None
    root = app_dir(app_id)
    if not root.is_dir():
        raise ValueError('Application does not exist')
    # Runtime lookup precedes state changes, so missing ARM runtime is explicit.
    runner = runtime()
    with (root/'operation.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('This application is already busy') from None
        record = json.loads((root/'app.json').read_text())
        env = os.environ.copy()
        env['WINEPREFIX'] = str(root/'prefix')
        # Separate Wine prefixes are configuration isolation, NOT a security sandbox.
        command = [runner, 'uninstaller'] if remove else (
            [runner, 'msiexec', '/i', str(binary)] if binary.suffix.lower() == '.msi'
            else [runner, str(binary)])
        record['status'] = 'running'
        save(root, record)
        with (root/'runtime.log').open('ab') as log:
            try:
                code = subprocess.run(command, env=env, cwd=root, stdout=log, stderr=log,
                                      stdin=subprocess.DEVNULL, check=False).returncode
            except OSError:
                record['status'] = 'failed'
                save(root, record)
                raise
        record['status'] = 'finished' if code == 0 else 'failed'
        record['last_exit_code'] = code
        save(root, record)
        if code:
            raise RuntimeError(f'Runtime exited with {code}; inspect the application log.')
        return code


def register(app_id, executable):
    root = app_dir(app_id)
    executable = validate_binary(executable)
    if not executable.is_relative_to((root/'prefix').resolve()):
        raise ValueError('Select an installed executable inside this application prefix')
    record = json.loads((root/'app.json').read_text())
    record['executable'] = str(executable)
    save(root, record)
    applications = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))/'applications'
    applications.mkdir(parents=True, exist_ok=True)
    # Desktop file values never contain user-provided names, paths or shell text.
    (applications/f'linux-desktop-{app_id}.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Windows App '+app_id[:8]+
        '\nExec=/usr/bin/linux-desktop-winapps --run '+app_id+
        '\nIcon=application-x-executable\nCategories=Utility;\nTerminal=false\n')


def export_log(app_id, destination):
    root = app_dir(app_id)
    text = (root/'runtime.log').read_text(errors='replace') if (root/'runtime.log').exists() else ''
    text = text.replace(str(Path.home()), '<HOME>')
    # Only the runtime log is exported. It may still contain application data.
    Path(destination).write_text(text)


def gui(initial=None, run_id=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox
    window = tk.Tk()
    window.title('Windows Applications · linux-desktop')
    window.geometry('720x420')
    heading = tk.Label(window, text='Windows Applications', font=('', 18))
    heading.pack(pady=10)
    tk.Label(window, text='Separate environments are not security sandboxes. Run trusted software only.').pack()
    listing = tk.Listbox(window)
    listing.pack(fill='both', expand=True, padx=12, pady=8)
    ids = []
    busy = False

    def refresh():
        ids.clear(); listing.delete(0, tk.END)
        for f in sorted(state_root().glob('*/app.json')):
            try:
                r = json.loads(f.read_text())
                app_dir(r['id'])
                ids.append(r['id'])
                listing.insert(tk.END, f"{r['name']} [{r['status']}]")
            except (ValueError, KeyError, OSError):
                continue

    def selected():
        index = listing.curselection()
        if not index:
            raise ValueError('Select an application first')
        return ids[index[0]]

    def task(fn):
        nonlocal busy
        if busy:
            messagebox.showinfo('Busy', 'Wait for the current operation to finish.'); return
        busy = True
        def work():
            try:
                fn()
                window.after(0, lambda: messagebox.showinfo('Done', 'Operation completed.'))
            except Exception as exc:
                message = str(exc)
                window.after(0, lambda: messagebox.showerror('Error', message))
            finally:
                def finish():
                    nonlocal busy
                    busy = False; refresh()
                window.after(0, finish)
        threading.Thread(target=work, daemon=True).start()

    def install(path=None):
        path = path or filedialog.askopenfilename(filetypes=[('Windows installers', '*.exe *.msi')])
        if path and messagebox.askyesno('Run Windows software?',
                f'Source: {path}\nThis program can access your files. Continue?'):
            def action():
                runtime()
                app_id = create_app(path)
                execute(app_id, path, install=True)
            task(action)

    def run(app_id=None):
        app_id = app_id or selected()
        record = json.loads((app_dir(app_id)/'app.json').read_text())
        if not record.get('executable'):
            exe = filedialog.askopenfilename(initialdir=app_dir(app_id)/'prefix',
                                             filetypes=[('Windows program', '*.exe')])
            if not exe: return
            register(app_id, exe)
            record = json.loads((app_dir(app_id)/'app.json').read_text())
        task(lambda: execute(app_id, record['executable']))

    def uninstall():
        app_id = selected()
        task(lambda: execute(app_id, None, remove=True))

    def export():
        app_id = selected()
        if not messagebox.askyesno('Review before sharing', 'Logs may contain application data. Export?'): return
        target = filedialog.asksaveasfilename(defaultextension='.log')
        if target: export_log(app_id, target)

    def guarded(fn):
        def invoke():
            try: fn()
            except Exception as exc: messagebox.showerror('Error', str(exc))
        return invoke

    bar = tk.Frame(window); bar.pack(pady=8)
    for label, fn in [('Install', install), ('Run / Create shortcut', run), ('Uninstall', uninstall), ('Export log', export),
                      ('Help', lambda: subprocess.Popen(['/usr/bin/linux-desktop-help']))]:
        tk.Button(bar, text=label, command=guarded(fn)).pack(side='left', padx=3)
    def close():
        if busy: messagebox.showinfo('Busy', 'Finish the operation before closing.'); return
        window.destroy()
    window.protocol('WM_DELETE_WINDOW', close)
    refresh()
    if initial: window.after(100, guarded(lambda: install(initial)))
    if run_id: window.after(100, guarded(lambda: run(run_id)))
    window.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('installer', nargs='?')
    parser.add_argument('--run')
    parser.add_argument('--doctor', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.exit(1, 'Run this manager as a regular desktop user.\n')
    if args.doctor:
        try: print(runtime())
        except RuntimeError as exc: parser.exit(1, str(exc)+'\n')
        return
    gui(args.installer, args.run)


if __name__ == '__main__':
    main()
