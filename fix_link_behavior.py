#!/usr/bin/env python3
"""Fix: remove `link:` from front-matter, put external URL inside post body."""

import os, re, glob

BASE = "/tmp/blog-content/source/_posts"
stats = {"gb": 0, "bs": 0, "no_link": 0, "fixed": 0}

for folder in ["standards_gb", "standards_bs"]:
    path = os.path.join(BASE, folder)
    if not os.path.isdir(path):
        continue
    for f in sorted(glob.glob(os.path.join(path, "*.md"))):
        with open(f, "r", encoding="utf-8") as fh:
            content = fh.read()
        
        m = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not m:
            print(f"  SKIP (no fm): {os.path.basename(f)}")
            continue
        
        fm_raw = m.group(1)
        body_raw = m.group(2).strip()
        
        link_match = re.search(r'^link:\s*\'(.*?)\'\s*$', fm_raw, re.MULTILINE)
        if not link_match:
            stats["no_link"] += 1
            continue
        
        link_url = link_match.group(1)
        
        new_fm = re.sub(r'^link:.*\n?', '', fm_raw, flags=re.MULTILINE)
        new_fm = new_fm.rstrip()
        
        desc = body_raw if body_raw and body_raw not in ('N/A', 'OpenStd', '-') else ''
        
        new_body_parts = []
        if desc:
            new_body_parts.append(desc)
            new_body_parts.append("")
        
        is_placeholder = ('Missing' in link_url or 'missing' in link_url.lower() or 
                         'placeholder' in link_url.lower() or 'null' in link_url.lower() or 
                         link_url == '#')
        if not is_placeholder and 'mohurd' not in link_url.lower():
            new_body_parts.append(
                f'<a href="{link_url}" target="_blank" rel="noopener noreferrer" '
                f'style="display:inline-block;padding:10px 24px;background:#1a5f7a;'
                f'color:#fff;border-radius:6px;text-decoration:none;margin-top:12px;">'
                f'📄 查看完整標準原文 →</a>'
            )
        elif 'mohurd' in link_url.lower():
            new_body_parts.append(
                f'<a href="{link_url}" target="_blank" rel="noopener noreferrer" '
                f'style="display:inline-block;padding:10px 24px;background:#1a5f7a;'
                f'color:#fff;border-radius:6px;text-decoration:none;margin-top:12px;">'
                f'🏛️ 住房和城鄉建設部 →</a>'
            )
        
        new_body = '\n'.join(new_body_parts)
        new_content = f"---\n{new_fm}\n---\n\n{new_body}\n"
        
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        
        stats[folder.replace("standards_", "")] += 1
        stats["fixed"] += 1

print(f"✅ Done: {stats}")
print(f"  GB: {stats['gb']} fixed")
print(f"  BS: {stats['bs']} fixed")
print(f"  No link (skipped): {stats['no_link']}")
