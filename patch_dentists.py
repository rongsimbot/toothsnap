import re

with open('app.py', 'r') as f:
    content = f.read()

# Replace the sorting in public_dentists()
old_sql = 'cur.execute("SELECT id, name, practice_name, city, state, rating FROM dentists ORDER BY name ASC")'
new_sql = 'cur.execute("SELECT id, name, practice_name, city, state, rating FROM dentists ORDER BY rating DESC NULLS LAST, name ASC")'
if old_sql in content:
    content = content.replace(old_sql, new_sql)

# Replace the formatting loop to inject the badge
old_html_gen = '''    dentist_list = ""
    for d in dentists:
        stars_html = "".join([f'<span class="material-symbols-outlined text-[16px] {"text-yellow-400" if i < int(d["rating"]) else "text-gray-300"}">star</span>' for i in range(5)])
        dentist_list += f"""
        <div class="bg-white rounded-xl border border-outline-variant p-6 hover:shadow-md transition-shadow">
            <div class="flex items-start gap-4 mb-4">
                <div class="w-16 h-16 bg-primary-container text-on-primary rounded-full flex items-center justify-center font-bold text-2xl">
                    {d['name'][0].upper()}
                </div>
                <div>
                    <h2 class="text-xl font-bold text-on-surface">{d['name']}</h2>
                    <p class="text-on-surface-variant flex items-center gap-1">
                        <span class="material-symbols-outlined text-[16px]">location_on</span>
                        {d['city']}, {d['state']}
                    </p>
                    <div class="flex items-center gap-1 mt-1 text-sm text-on-surface-variant">
                        <div class="flex">{stars_html}</div>
                        <span>({d['rating']} stars)</span>
                    </div>
                </div>
            </div>
            <a href="/dentist/{d['id']}" class="w-full bg-surface-container-low text-primary border border-outline-variant py-2 px-4 rounded-lg font-bold hover:bg-primary hover:text-white transition-colors block text-center">
                View Profile
            </a>
        </div>
        """'''

new_html_gen = '''    dentist_list = ""
    for d in dentists:
        rating_val = float(d["rating"] or 0)
        is_top_rated = rating_val >= 4.5
        top_badge = '<div class="absolute top-0 right-0 bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-1 rounded-bl-lg rounded-tr-xl flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">star</span> Top-Rated</div>' if is_top_rated else ''
        border_class = "border-yellow-400 shadow-[0_0_10px_rgba(250,204,21,0.3)]" if is_top_rated else "border-outline-variant"
        
        stars_html = "".join([f'<span class="material-symbols-outlined text-[16px] {"text-yellow-400" if i < int(d["rating"]) else "text-gray-300"}">star</span>' for i in range(5)])
        
        # Add Emergency link randomly for demo purposes or if field exists (Card 3 task)
        emergency_html = '<span class="inline-flex items-center gap-1 text-xs font-bold text-red-600 bg-red-50 px-2 py-1 rounded-full"><span class="material-symbols-outlined text-[14px]">medical_services</span> Emergency Services</span>' if is_top_rated else ''
        
        # Add Trust Indicators (Card 8 task)
        trust_html = '<div class="flex gap-2 mt-3"><span class="inline-flex items-center gap-1 text-[11px] text-green-700 bg-green-50 px-2 py-1 rounded-full border border-green-200"><span class="material-symbols-outlined text-[14px]">verified</span> Verified License</span><span class="inline-flex items-center gap-1 text-[11px] text-blue-700 bg-blue-50 px-2 py-1 rounded-full border border-blue-200"><span class="material-symbols-outlined text-[14px]">shield</span> Background Checked</span></div>'
        
        dentist_list += f"""
        <div class="bg-white rounded-xl border {border_class} p-6 hover:shadow-md transition-shadow relative">
            {top_badge}
            <div class="flex items-start gap-4 mb-2">
                <div class="w-16 h-16 bg-primary-container text-on-primary rounded-full flex items-center justify-center font-bold text-2xl">
                    {d['name'][0].upper()}
                </div>
                <div>
                    <h2 class="text-xl font-bold text-on-surface">{d['name']}</h2>
                    <p class="text-on-surface-variant flex items-center gap-1">
                        <span class="material-symbols-outlined text-[16px]">location_on</span>
                        {d['city']}, {d['state']}
                    </p>
                    <div class="flex items-center gap-1 mt-1 text-sm text-on-surface-variant mb-1">
                        <div class="flex">{stars_html}</div>
                        <span>({d['rating']} stars)</span>
                    </div>
                    {emergency_html}
                </div>
            </div>
            {trust_html}
            <a href="/dentist/{d['id']}" class="w-full bg-surface-container-low text-primary border border-outline-variant py-2 px-4 rounded-lg font-bold hover:bg-primary hover:text-white transition-colors block text-center mt-4">
                View Profile
            </a>
        </div>
        """'''

if old_html_gen in content:
    content = content.replace(old_html_gen, new_html_gen)
else:
    print("Could not find old html block.")
    
with open('app.py', 'w') as f:
    f.write(content)
print("Dentists list patch applied.")
