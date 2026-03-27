import re

with open('app.py', 'r') as f:
    content = f.read()

# Add instruments route
if '@app.route("/instruments")' not in content:
    instruments_route = """
@app.route("/instruments")
def instruments():
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ToothSnap | Instruments</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
        <script>
            tailwind.config = { theme: { extend: { colors: { "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff", "surface": "#fbf9f8", "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2" } } } }
        </script>
    </head>
    <body class="bg-surface text-on-surface">
        <!-- Navbar -->
        <nav class="bg-surface-container-lowest border-b border-outline-variant px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
            <a href="/" class="flex items-center gap-3">
                <span class="font-bold text-2xl tracking-tight text-primary drop-shadow-md font-['Plus_Jakarta_Sans']">Tooth<span class="text-[#006098]">Snap</span></span>
                <span class="material-symbols-outlined text-[#006098] text-[32px] font-medium" style="font-variation-settings: 'FILL' 1; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));">dentistry</span>
            </a>
            <div class="hidden md:flex gap-8 font-semibold text-[15px] text-on-surface-variant">
                <a href="/" class="hover:text-primary transition-colors">Home</a>
                <a href="/education" class="hover:text-primary transition-colors">Education</a>
                <a href="/dentists" class="hover:text-primary transition-colors">Find a Dentist</a>
            </div>
        </nav>
        <div class="max-w-4xl mx-auto py-12 px-6">
            <div class="text-center mb-12">
                <h1 class="text-4xl font-extrabold text-primary mb-4">Dental Instruments Guide</h1>
                <p class="text-xl text-on-surface-variant">Learn about the common tools used during your visit.</p>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 h-96 overflow-y-auto pr-2">
                <div class="bg-white p-4 rounded-xl shadow border border-outline-variant flex gap-4">
                    <div class="w-20 h-20 bg-gray-200 rounded-lg flex items-center justify-center flex-shrink-0"><span class="material-symbols-outlined text-4xl text-gray-500">search</span></div>
                    <div><h3 class="font-bold text-lg">Mouth Mirror</h3><p class="text-sm text-gray-600">A small mirror attached to a handle. It allows the dentist to see places in the mouth that are hard to reach.</p></div>
                </div>
                <div class="bg-white p-4 rounded-xl shadow border border-outline-variant flex gap-4">
                    <div class="w-20 h-20 bg-gray-200 rounded-lg flex items-center justify-center flex-shrink-0"><span class="material-symbols-outlined text-4xl text-gray-500">cleaning_services</span></div>
                    <div><h3 class="font-bold text-lg">Scaler</h3><p class="text-sm text-gray-600">Used to scrape and remove plaque and tartar build-up from the teeth and beneath the gum line.</p></div>
                </div>
                <div class="bg-white p-4 rounded-xl shadow border border-outline-variant flex gap-4">
                    <div class="w-20 h-20 bg-gray-200 rounded-lg flex items-center justify-center flex-shrink-0"><span class="material-symbols-outlined text-4xl text-gray-500">explore</span></div>
                    <div><h3 class="font-bold text-lg">Explorer</h3><p class="text-sm text-gray-600">A sharp-pointed instrument used to probe the teeth for cavities and check the hardness of the enamel.</p></div>
                </div>
                <div class="bg-white p-4 rounded-xl shadow border border-outline-variant flex gap-4">
                    <div class="w-20 h-20 bg-gray-200 rounded-lg flex items-center justify-center flex-shrink-0"><span class="material-symbols-outlined text-4xl text-gray-500">air</span></div>
                    <div><h3 class="font-bold text-lg">Suction Device</h3><p class="text-sm text-gray-600">A tube that removes saliva, blood, and debris from the mouth to keep it clean and dry during procedures.</p></div>
                </div>
                <div class="bg-white p-4 rounded-xl shadow border border-outline-variant flex gap-4">
                    <div class="w-20 h-20 bg-gray-200 rounded-lg flex items-center justify-center flex-shrink-0"><span class="material-symbols-outlined text-4xl text-gray-500">build</span></div>
                    <div><h3 class="font-bold text-lg">Dental Drill</h3><p class="text-sm text-gray-600">A high-speed tool used to remove decay and shape the tooth structure before inserting a filling or crown.</p></div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)
"""
    content = content.replace("if __name__ == '__main__':", instruments_route + "\nif __name__ == '__main__':")

# Update Education page with Did You Know and Resources
education_route_pattern = r'@app\.route\("/education"\).*?def education\(\):.*?html = f?\'\'\'(.*?)\'\'\'.*?return render_template_string\(html\)'
education_match = re.search(education_route_pattern, content, re.DOTALL)

if education_match:
    old_html = education_match.group(1)
    
    new_sections = """
        <!-- Did You Know Section -->
        <div class="mt-8 bg-blue-50 border border-blue-200 rounded-xl p-6 text-center">
            <h3 class="text-xl font-bold text-primary mb-2 flex justify-center items-center gap-2"><span class="material-symbols-outlined">lightbulb</span> Did You Know?</h3>
            <p id="fact-display" class="text-lg font-medium text-gray-700 italic">"Your tooth enamel is the hardest substance in your entire body."</p>
        </div>
        <script>
            const facts = [
                "Your tooth enamel is the hardest substance in your entire body.",
                "If you don't floss, you miss cleaning 40% of your tooth surfaces.",
                "The average person spends 38.5 days brushing their teeth over their lifetime.",
                "Saliva helps protect your teeth from decay by neutralizing acids."
            ];
            let factIndex = 0;
            setInterval(() => {
                factIndex = (factIndex + 1) % facts.length;
                document.getElementById('fact-display').innerText = '"' + facts[factIndex] + '"';
            }, 5000);
        </script>

        <!-- External Resources Section -->
        <div class="mt-12">
            <h3 class="text-2xl font-bold mb-4 border-b pb-2">External Dental Resources</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <a href="https://www.ada.org/" target="_blank" class="block p-4 border rounded-lg hover:shadow-md transition bg-white">
                    <h4 class="font-bold text-lg text-primary">American Dental Association</h4>
                    <p class="text-sm text-gray-600">The nation's leading advocate for oral health. Find reliable dental information.</p>
                </a>
                <a href="https://www.cdc.gov/oralhealth/index.html" target="_blank" class="block p-4 border rounded-lg hover:shadow-md transition bg-white">
                    <h4 class="font-bold text-lg text-primary">CDC Oral Health</h4>
                    <p class="text-sm text-gray-600">Public health resources, statistics, and preventive care guidelines.</p>
                </a>
                <a href="https://www.mouthhealthy.org/" target="_blank" class="block p-4 border rounded-lg hover:shadow-md transition bg-white">
                    <h4 class="font-bold text-lg text-primary">MouthHealthy</h4>
                    <p class="text-sm text-gray-600">A-Z topics on dental care, diet tips, and oral health by the ADA.</p>
                </a>
            </div>
        </div>
    """
    
    if "Did You Know?" not in old_html:
        # Insert before the Need personalized advice section
        new_html = old_html.replace('<div class="mt-12 text-center border-t border-outline-variant pt-8">', new_sections + '\n        <div class="mt-12 text-center border-t border-outline-variant pt-8">')
        content = content.replace(old_html, new_html)

with open('app.py', 'w') as f:
    f.write(content)
print("Patch applied.")
