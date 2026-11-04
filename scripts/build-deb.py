#!/usr/bin/env python3
from pathlib import Path
import os
import hashlib
import zipfile
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
def main():
    dest = ROOT/'build/package'
    if dest.exists(): shutil.rmtree(dest)
    def copy(source, target, executable=False):
        out = dest/target
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/source, out)
        out.chmod(0o755 if executable else 0o644)
    for source, target in [('src/winapps.py','usr/bin/linux-desktop-winapps'),('src/help.py','usr/bin/linux-desktop-help')]:
        copy(source,target,True)
    for name in ['linux-desktop-help.desktop','linux-desktop-winapps.desktop']:
        copy('config/'+name, 'usr/share/applications/'+name)
    copy('config/runtimes.json','etc/linux-desktop/runtimes.json')
    copy('config/90-linux-desktop.gschema.override','usr/share/glib-2.0/schemas/90-linux-desktop.gschema.override')
    for page in (ROOT/'tutorial').glob('*.html'):
        copy(str(page.relative_to(ROOT)), 'usr/share/linux-desktop/tutorial/'+page.name)
    copy('LICENSE', 'usr/share/doc/linux-desktop/copyright')
    copy('docs/TUTORIAL-LICENSE', 'usr/share/doc/linux-desktop/tutorial-license')
    control=dest/'DEBIAN'; control.mkdir()
    version=(ROOT/'VERSION').read_text().strip()
    (control/'control').write_text(f"""Package: linux-desktop
Version: {version}
Section: x11
Priority: optional
Architecture: all
Maintainer: linux-desktop contributors <noreply@users.noreply.github.com>
Depends: python3, python3-tk, xdg-utils
Recommends: linux-desktop-panel
Description: Desktop integration, Windows application manager and offline tutorials
 Experimental source preview; not a certified operating system image.
""")
    (control/'triggers').write_text('activate-noawait /usr/share/glib-2.0/schemas\nactivate-noawait /usr/share/applications\n')
    # Preserve administrator runtime changes during upgrades.
    (control/'conffiles').write_text('/etc/linux-desktop/runtimes.json\n')
    env=os.environ.copy(); env.setdefault('SOURCE_DATE_EPOCH','1793740800')
    out=ROOT/'build'/f'linux-desktop_{version}_all.deb'
    subprocess.run(['dpkg-deb','--root-owner-group','--build',str(dest),str(out)],check=True,env=env)
    print(out)
    archive=ROOT/'third_party/dash-to-panel-v74.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!='a4344e3143b37aafd1dff71d2daec30a953f55a44fd606e3fe10d46ee1c1582a':
        raise ValueError('Panel extension checksum mismatch')
    panel=ROOT/'build/panel'
    if panel.exists(): shutil.rmtree(panel)
    extension=panel/'usr/share/gnome-shell/extensions/dash-to-panel@jderose9.github.com'
    extension.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:
        for name in zipped.namelist():
            if not (extension/name).resolve().is_relative_to(extension.resolve()):
                raise ValueError('Archive path traversal')
        zipped.extractall(extension)
    doc=panel/'usr/share/doc/linux-desktop-panel'; doc.mkdir(parents=True)
    shutil.copy2(extension/'COPYING',doc/'copyright')
    meta=panel/'DEBIAN'; meta.mkdir()
    (meta/'control').write_text('Package: linux-desktop-panel\nVersion: 74-1\nArchitecture: all\n'
        'Maintainer: linux-desktop contributors <noreply@users.noreply.github.com>\n'
        'Depends: gnome-shell (>= 46)\nDescription: Unmodified Dash to Panel extension (GPL-2.0)\n')
    subprocess.run(['dpkg-deb','--root-owner-group','--build',str(panel),
                    str(ROOT/'build/linux-desktop-panel_74-1_all.deb')],check=True,env=env)
if __name__=='__main__': main()
