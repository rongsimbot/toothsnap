import sys

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "r") as f:
    code = f.read()

education_route = """
@app.route("/education")
def education():
    if "user_id" not in session:
        return redirect("/register?prompt=education")
        
    html = f\"\"\"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | Education Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{ theme: {{ extend: {{ colors: {{ "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff", "surface": "#fbf9f8", "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2" }} }} }} }}
    </script>
</head>
<body class="bg-surface text-on-surface">
    <!-- Navbar -->
    <nav class="bg-white border-b border-outline-variant px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <a href="/" class="flex items-center gap-3">
            <span class="material-symbols-outlined text-primary text-[32px]">dentistry</span>
            <span class="font-bold text-2xl tracking-tight font-['\''Plus_Jakarta_Sans'\'']">Tooth<span class="text-primary">Snap</span></span>
        </a>
        <div class="flex gap-8 font-semibold text-[15px] text-on-surface-variant">
            <a href="/dashboard" class="text-primary">My Account</a>
        </div>
    </nav>

    <div class="max-w-4xl mx-auto py-12 px-6">
        <div class="text-center mb-12">
            <h1 class="text-4xl font-extrabold font-['\''Plus_Jakarta_Sans'\''] text-primary mb-4">Dental Hygiene Education Center</h1>
            <p class="text-xl text-on-surface-variant max-w-2xl mx-auto">Expert tips and guides for maintaining a healthy, beautiful smile for you and your family.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <!-- Kids Section -->
            <div class="bg-white rounded-2xl border border-outline-variant overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                <div class="h-48 bg-blue-100 flex items-center justify-center">
                    <span class="material-symbols-outlined text-[80px] text-primary">child_care</span>
                </div>
                <div class="p-6">
                    <h2 class="text-2xl font-bold mb-3 text-on-surface">Pediatric Oral Care</h2>
                    <p class="text-on-surface-variant mb-4">Learn how to build strong brushing habits for your kids, understand teething, and prevent early cavities.</p>
                    <ul class="space-y-2 text-sm text-on-surface-variant font-medium mb-6">
                        <li class="flex items-center gap-2"><span class="material-symbols-outlined text-green-500 text-[18px]">check_circle</span> Brushing techniques for toddlers</li>
                        <li class="flex items-center gap-2"><span class="material-symbols-outlined text-green-500 text-[18px]">check_circle</span> Choosing the right fluoride toothpaste</li>
                        <li class="flex items-center gap-2"><span class="material-symbols-outlined text-green-500 text-[18px]">check_circle</span> When to schedule the first dentist visit</li>
                    </ul>
                    <button class="w-full bg-surface-container-low text-primary py-2 rounded-lg font-bold border border-outline-variant hover:bg-primary hover:text-white transition-colors">Read Guide</button>
                </div>
            </div>
            
            <!-- Adults Section -->
            <div class="bg-white rounded-2xl border border-outline-variant overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                <div class="h-48 bg-purple-100 flex items-center justify-center">
                    <span class="material-symbols-outlined text-[80px] text-purple-600">person</span>
                </div>
                <div class="p-6">
                    <h2 class="text-2xl font-bold mb-3 text-on-surface">Adult Dental Hygiene</h2>
                    <p class="text-on-surface-variant mb-4">Advanced care for adult teeth, including flossing effectively, preventing gum disease, and protecting enamel.</p>
                    <ul class="space-y-2 text-sm text-on-surface-variant font-medium mb-6">
                        <li class="flex items-center gap-2"><span class="material-symbols-outlined text-green-500 text-[18px]">check_circle</span> The proper way to floss (C-shape method)</li>
                        <li class="flex items-center gap-2"><span class="material-symbols-outlined text-green-500 text-[18px]">check_circle</span> Impact of diet and coffee on enamel</li>
                        <li class="flex items-center gap-2"><span class="material-symbols-outlined text-green-500 text-[18px]">check_circle</span> Signs of gingivitis and gum disease</li>
                    </ul>
                    <button class="w-full bg-surface-container-low text-primary py-2 rounded-lg font-bold border border-outline-variant hover:bg-primary hover:text-white transition-colors">Read Guide</button>
                </div>
            </div>
        </div>
        
        <div class="mt-12 text-center border-t border-outline-variant pt-8">
            <h3 class="text-2xl font-bold mb-4">Need personalized advice?</h3>
            <a href="/dentists" class="inline-flex items-center justify-center gap-2 bg-primary text-on-primary px-8 py-3 rounded-full font-bold shadow-sm hover:bg-primary-container transition-colors">
                <span class="material-symbols-outlined">search</span> Find a Dentist Near You
            </a>
        </div>
    </div>
</body>
</html>\"\"\"
    return render_template_string(html)
"""

if "def education():" not in code:
    parts = code.split("if __name__ ==")
    code = parts[0] + education_route + "\nif __name__ ==" + parts[1]

# Make sure the /register route handles the prompt
old_register_prompt = """<p class="text-on-surface-variant">Join ToothSnap to manage your orders</p>"""
new_register_prompt = """<p class="text-on-surface-variant">
                {f'<span class="text-primary font-bold block mb-2">You must sign up to view the Education Center.</span>' if request.args.get("prompt") == "education" else 'Join ToothSnap to manage your orders'}
            </p>"""

if old_register_prompt in code:
    code = code.replace(old_register_prompt, new_register_prompt)

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "w") as f:
    f.write(code)

print("EDUCATION ROUTE INJECTED")
