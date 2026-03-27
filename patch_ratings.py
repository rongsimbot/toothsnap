import re

with open("app.py", "r") as f:
    code = f.read()

# 1. Fix `/dentists` route query to include rating
query_old = """cur.execute("SELECT id, name, practice_name, city, state FROM dentists ORDER BY name ASC")"""
query_new = """cur.execute("SELECT id, name, practice_name, city, state, rating FROM dentists ORDER BY name ASC")"""
code = code.replace(query_old, query_new)

query_old2 = """cur.execute("SELECT id, name, practice_name, city, state FROM dentists WHERE name ILIKE %s OR practice_name ILIKE %s OR city ILIKE %s OR state ILIKE %s ORDER BY name ASC", (q, q, q, q))"""
query_new2 = """cur.execute("SELECT id, name, practice_name, city, state, rating FROM dentists WHERE name ILIKE %s OR practice_name ILIKE %s OR city ILIKE %s OR state ILIKE %s ORDER BY name ASC", (q, q, q, q))"""
code = code.replace(query_old2, query_new2)

# 2. Fix the dentists dictionary mapping
dict_old = """dentists = [{"id": r[0], "name": r[1], "practice_name": r[2], "city": r[3], "state": r[4]} for r in results]"""
dict_new = """dentists = [{"id": r[0], "name": r[1], "practice_name": r[2], "city": r[3], "state": r[4], "rating": r[5]} for r in results]"""
code = code.replace(dict_old, dict_new)

# 3. Add Rating column to the table header in /dentists
thead_old = """<th class="py-4 px-6">Dentist Name</th>
                        <th class="py-4 px-6 hidden sm:table-cell">Practice</th>
                        <th class="py-4 px-6">Location</th>"""
thead_new = """<th class="py-4 px-6">Dentist Name</th>
                        <th class="py-4 px-6 hidden sm:table-cell">Practice</th>
                        <th class="py-4 px-6">Location</th>
                        <th class="py-4 px-6 text-center">Rating</th>"""
code = code.replace(thead_old, thead_new)

# 4. Add Rating column data to the table rows in /dentists
tr_old = """<td class="py-4 px-6">
                            <a href="/dentist/{d['id']}" class="font-bold text-primary hover:underline flex items-center gap-1">{d["name"]} <span class="material-symbols-outlined text-[14px]">open_in_new</span></a>
                        </td>
                        <td class="py-4 px-6 hidden sm:table-cell text-on-surface-variant">{d["practice_name"] or "-"}</td>
                        <td class="py-4 px-6 text-on-surface-variant">{d["city"] or "-"}, {d["state"] or "-"}</td>
                    </tr>"""
tr_new = """<td class="py-4 px-6">
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
                    </tr>"""
code = code.replace(tr_old, tr_new)

# 5. Fix the search popup hardcoded stars
popup_stars_old = """<div class="popup-header">
                            <div style="color: #FFD700; font-size: 14px; margin-bottom: 4px; display: flex; gap: 2px; align-items: center;">
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span style="color: #ffffff; margin-left: 4px; font-size: 12px; font-weight: bold; opacity: 0.9;">5.0</span>
                            </div>"""
popup_stars_new = """<div class="popup-header">
                            <div style="color: #FFD700; font-size: 14px; margin-bottom: 4px; display: flex; gap: 2px; align-items: center;" title="View reviews on profile">
                                <span class="material-symbols-outlined" style="font-size: 14px; font-variation-settings: 'FILL' 1;">star</span>
                                <span style="color: #ffffff; margin-left: 4px; font-size: 12px; font-weight: bold; opacity: 0.9;">${d.rating || 'New'}</span>
                            </div>"""
code = code.replace(popup_stars_old, popup_stars_new)

with open("app.py", "w") as f:
    f.write(code)

print("Patch applied")
