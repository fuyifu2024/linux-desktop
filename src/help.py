#!/usr/bin/python3
import os
from pathlib import Path
import subprocess

LANGS = {'zh_CN': 'zh-Hans', 'zh_SG': 'zh-Hans', 'zh_TW': 'zh-Hant', 'zh_HK': 'zh-Hant',
         'ja': 'ja', 'ru': 'ru', 'fr': 'fr', 'es': 'es', 'en': 'en'}

def language(value):
    value = value.split('.')[0].split('@')[0]
    return LANGS.get(value, LANGS.get(value.split('_')[0], 'en'))

def main():
    lang = language(os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG', 'en'))
    page = Path('/usr/share/linux-desktop/tutorial') / (lang + '.html')
    subprocess.run(['xdg-open', page.as_uri()], check=True)

if __name__ == '__main__': main()
