import sys

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "r") as f:
    code = f.read()

# 1. Update Map Popup
old_popup_header = """<h4 style="font-weight: 800; font-size: 16px; margin: 0; font-family: 'Plus Jakarta Sans', sans-serif;">${{d.practice_name}}</h4>"""
new_popup_header = """<a href="/dentist/${{d.id}}" style="text-decoration: none; color: inherit;"><h4 style="font-weight: 800; font-size: 16px; margin: 0; font-family: 'Plus Jakarta Sans', sans-serif; cursor: pointer; color: #006098; transition: color 0.2s;">${{d.practice_name}} <span class="material-symbols-outlined" style="font-size: 14px; vertical-align: middle;">open_in_new</span></h4></a>"""

if old_popup_header in code:
    code = code.replace(old_popup_header, new_popup_header)

# 2. Update /dentists Directory
old_dir_name = """<div class="font-bold text-on-surface">{d["name"]}</div>"""
new_dir_name = """<a href="/dentist/{d['id']}" class="font-bold text-primary hover:underline flex items-center gap-1">{d["name"]} <span class="material-symbols-outlined text-[14px]">open_in_new</span></a>"""

if old_dir_name in code:
    code = code.replace(old_dir_name, new_dir_name)

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "w") as f:
    f.write(code)

print("LINKS PATCHED")
