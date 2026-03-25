import sys

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "r") as f:
    code = f.read()

# Careful with Python f-string escaping vs JS template literal
old_popup = """<div class="popup-header">
                            <h4 style="font-weight: 800; font-size: 16px; margin: 0; font-family: 'Plus Jakarta Sans', sans-serif;">${{d.practice_name}}</h4>"""

new_popup = """<div class="popup-header">
                            <div style="color: #FFD700; font-size: 14px; margin-bottom: 4px; display: flex; gap: 2px; align-items: center;">
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span style="color: #ffffff; margin-left: 4px; font-size: 12px; font-weight: bold; opacity: 0.9;">5.0</span>
                            </div>
                            <h4 style="font-weight: 800; font-size: 16px; margin: 0; font-family: 'Plus Jakarta Sans', sans-serif;">${{d.practice_name}}</h4>"""

if old_popup in code:
    code = code.replace(old_popup, new_popup)
    with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "w") as f:
        f.write(code)
    print("SUCCESS")
else:
    print("NOT FOUND")
