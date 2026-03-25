import sys

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "r") as f:
    code = f.read()

if "generate_password_hash" not in code:
    code = code.replace("from flask import Flask", "from werkzeug.security import generate_password_hash, check_password_hash\nfrom flask import Flask")

with open("/home/lo/.openclaw/workspace/toothsnap/patch_auth.py", "r") as f:
    auth_routes = f.read()

if "@app.route(\"/login\")" not in code:
    parts = code.split("if __name__ ==")
    code = parts[0] + auth_routes + "\nif __name__ ==" + parts[1]

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "w") as f:
    f.write(code)

with open("/home/lo/.openclaw/workspace/toothsnap/index.html", "r") as f:
    html = f.read()

old_btn = """<button class="p-2 text-on-surface-variant hover:text-primary transition-colors">
<span class="material-symbols-outlined" data-icon="account_circle">account_circle</span>
</button>"""

new_btn = """<a href="/dashboard" class="p-2 text-on-surface-variant hover:text-primary transition-colors">
<span class="material-symbols-outlined" data-icon="account_circle">account_circle</span>
</a>"""

html = html.replace(old_btn, new_btn)

with open("/home/lo/.openclaw/workspace/toothsnap/index.html", "w") as f:
    f.write(html)
