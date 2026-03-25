import sys

GA4_CODE = """
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-XXXXXXXXXX');
    </script>
"""

with open("/home/lo/.openclaw/workspace/toothsnap/index.html", "r") as f:
    html = f.read()

if "G-XXXXXXXXXX" not in html:
    html = html.replace("</head>", GA4_CODE + "</head>")
    with open("/home/lo/.openclaw/workspace/toothsnap/index.html", "w") as f:
        f.write(html)

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "r") as f:
    code = f.read()

if "G-XXXXXXXXXX" not in code:
    code = code.replace("</head>", GA4_CODE + "</head>")
    with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "w") as f:
        f.write(code)
