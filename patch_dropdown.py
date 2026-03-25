import sys

with open("/home/lo/.openclaw/workspace/toothsnap/index.html", "r") as f:
    html = f.read()

# Update Education Link
html = html.replace('href="#">Education</a>', 'href="/education">Education</a>')

# Add Dropdown
old_nav = """<a class="text-[#1b1c1c] font-medium font-headline tracking-tight hover:scale-[1.02] hover:text-[#006098] transition-all duration-300" href="/dentist/register">Dentist Registration</a>"""

new_nav = """
<div class="relative group">
  <button class="text-[#1b1c1c] font-medium font-headline tracking-tight hover:text-[#006098] transition-all duration-300 flex items-center gap-1">
    Registration <span class="material-symbols-outlined text-[16px]">expand_more</span>
  </button>
  <div class="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border border-outline-variant opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 overflow-hidden z-50">
    <a href="/register?type=patient" class="block px-4 py-3 text-sm text-on-surface hover:bg-surface-container-low border-b border-outline-variant transition-colors flex items-center gap-2">
      <span class="material-symbols-outlined text-primary text-[18px]">person</span> I'm a Patient
    </a>
    <a href="/dentist/register" class="block px-4 py-3 text-sm text-on-surface hover:bg-surface-container-low transition-colors flex items-center gap-2">
      <span class="material-symbols-outlined text-primary text-[18px]">dentistry</span> I'm a Dentist
    </a>
  </div>
</div>
"""

if old_nav in html:
    html = html.replace(old_nav, new_nav)

with open("/home/lo/.openclaw/workspace/toothsnap/index.html", "w") as f:
    f.write(html)

print("DROPDOWN APPLIED")
