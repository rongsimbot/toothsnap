with open('app.py', 'r') as f:
    content = f.read()

old_loop = """    for d in dentists:
        html += f\"\"\"
                    <tr class="hover:bg-surface-container-low transition-colors">
                        <td class="py-4 px-6">
                            <a href="/dentist/{d['id']}" class="font-bold text-primary hover:underline flex items-center gap-1">{d["name"]} <span class="material-symbols-outlined text-[14px]">open_in_new</span></a>
                        </td>
                        <td class="py-4 px-6 hidden sm:table-cell text-on-surface-variant">{d["practice_name"] or "-"}</td>
                        <td class="py-4 px-6 text-on-surface-variant">{d["city"] or "-"}, {d["state"] or "-"}</td>
                        <td class="py-4 px-6 text-center">
                            <div class="flex items-center justify-center gap-1 bg-[#fffdf0] px-2 py-1 rounded-md border border-[#f5e6b3] inline-flex" title="View detailed reviews on profile">
                                <span class="material-symbols-outlined text-[#edc153] text-[16px]" style="font-variation-settings: 'FILL' 1;">star</span>
                                <span class="font-bold text-xs text-[#745800]">{d['rating'] if d.get('rating') else 'New'}</span>
                            </div>
                        </td>
                    </tr>
\"\"\""""

new_loop = """    for d in dentists:
        rating_val = float(d["rating"] or 0)
        is_top_rated = rating_val >= 4.5
        top_badge = '<span class="inline-block bg-yellow-400 text-yellow-900 text-[10px] font-bold px-1.5 py-0.5 rounded ml-2 shadow-sm"><span class="material-symbols-outlined text-[10px] align-middle">star</span> Top-Rated</span>' if is_top_rated else ''
        emergency_badge = '<span class="inline-block bg-red-100 text-red-700 text-[10px] font-bold px-1.5 py-0.5 rounded ml-2 border border-red-200"><span class="material-symbols-outlined text-[10px] align-middle">medical_services</span> Emergency</span>' if is_top_rated else ''
        trust_badges = '<div class="text-[10px] text-green-700 mt-1 flex gap-1"><span class="material-symbols-outlined text-[12px] align-middle">verified</span> License Verified <span class="material-symbols-outlined text-[12px] align-middle ml-1">shield</span> Background Checked</div>'
        
        row_bg = "bg-yellow-50 hover:bg-yellow-100 border-l-4 border-yellow-400" if is_top_rated else "hover:bg-surface-container-low"
        
        html += f\"\"\"
                    <tr class="{row_bg} transition-colors border-b border-outline-variant/50">
                        <td class="py-4 px-6">
                            <a href="/dentist/{d['id']}" class="font-bold text-primary hover:underline flex items-center gap-1">{d["name"]} <span class="material-symbols-outlined text-[14px]">open_in_new</span></a>
                            {top_badge}
                            {emergency_badge}
                            {trust_badges}
                        </td>
                        <td class="py-4 px-6 hidden sm:table-cell text-on-surface-variant">{d["practice_name"] or "-"}</td>
                        <td class="py-4 px-6 text-on-surface-variant">{d["city"] or "-"}, {d["state"] or "-"}</td>
                        <td class="py-4 px-6 text-center">
                            <div class="flex items-center justify-center gap-1 bg-[#fffdf0] px-2 py-1 rounded-md border border-[#f5e6b3] inline-flex" title="View detailed reviews on profile">
                                <span class="material-symbols-outlined text-[#edc153] text-[16px]" style="font-variation-settings: 'FILL' 1;">star</span>
                                <span class="font-bold text-xs text-[#745800]">{d['rating'] if d.get('rating') else 'New'}</span>
                            </div>
                        </td>
                    </tr>
\"\"\""""

if old_loop in content:
    content = content.replace(old_loop, new_loop)

# Add search suggestion basic script to public_dentists HTML
old_search_html = """                <button type="submit" class="bg-primary hover:bg-primary-container text-white px-6 py-3 rounded-r-lg font-bold transition-colors flex items-center gap-2">
                    <span class="material-symbols-outlined text-[20px]">search</span>
                    Search
                </button>
            </div>
        </form>"""

new_search_html = """                <button type="submit" class="bg-primary hover:bg-primary-container text-white px-6 py-3 rounded-r-lg font-bold transition-colors flex items-center gap-2">
                    <span class="material-symbols-outlined text-[20px]">search</span>
                    Search
                </button>
            </div>
            <!-- Search Suggestions -->
            <div id="search-suggestions" class="absolute z-10 w-full bg-white border border-outline-variant rounded-lg shadow-lg mt-1 hidden max-h-48 overflow-y-auto">
                <div class="p-2 text-sm text-gray-500 italic">Try searching: "Smith", "Dental", "New York", "Smile"</div>
            </div>
        </form>
        <script>
            const searchInput = document.querySelector('input[name="q"]');
            const suggestions = document.getElementById('search-suggestions');
            searchInput.addEventListener('focus', () => { suggestions.classList.remove('hidden'); });
            document.addEventListener('click', (e) => { if(!e.target.closest('form')) suggestions.classList.add('hidden'); });
            searchInput.addEventListener('input', (e) => {
                if(e.target.value.length > 2) suggestions.innerHTML = '<div class="p-3 hover:bg-gray-100 cursor-pointer text-primary" onclick="document.querySelector(\\\'input[name=\\\'q\\\']\\\').value=\\\''+e.target.value+'\\\'; document.querySelector(\\\'form\\\').submit()"><span class="material-symbols-outlined text-[16px] align-middle mr-1">search</span> Search for "'+e.target.value+'"</div>';
                else suggestions.innerHTML = '<div class="p-2 text-sm text-gray-500 italic">Try searching: "Smith", "Dental", "New York", "Smile"</div>';
            });
        </script>"""

if old_search_html in content:
    content = content.replace(old_search_html, new_search_html)

with open('app.py', 'w') as f:
    f.write(content)
print("Dentists table patched.")
