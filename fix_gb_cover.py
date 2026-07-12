#!/usr/bin/env python3
"""Fix GB cover URLs: replace %20 with literal + to match R2 filenames."""

import os, re, glob

BASE = "/tmp/blog-content/source/_posts/standards_gb"
fixed = 0
no_cover = 0

for f in sorted(glob.glob(os.path.join(BASE, "*.md"))):
    with open(f) as fh:
        content = fh.read()
    
    # Find cover line
    m = re.search(r'^cover:\s*(.+)$', content, re.MULTILINE)
    if not m:
        no_cover += 1
        continue
    
    cover = m.group(1).strip().strip("'").strip('"')
    if '%20' in cover and 'missing' not in cover.lower() or '+' in cover and 'missing' not in cover.lower():
        # Replace %20 and + with _
        new_cover = cover.replace('%20', '_').replace('+', '_')
        content = content.replace(cover, new_cover)
        with open(f, 'w') as fh:
            fh.write(content)
        fixed += 1
    elif 'missing' in cover.lower() or not cover:
        no_cover += 1

print(f"Fixed: {fixed}")
print(f"No cover / missing: {no_cover}")
print(f"Total GB posts: {fixed + no_cover}")
