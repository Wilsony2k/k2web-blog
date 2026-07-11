#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime
from pathlib import Path
import shutil

SOURCE_DIR = Path('/var/www/k2-web/N8N')
TARGET_DIR = Path('/tmp/blog-content/source/_posts')

# Ensure target directory exists
TARGET_DIR.mkdir(parents=True, exist_ok=True)

def extract_date(date_str):
    """Extract and convert date to YYYY-MM-DD format."""
    if not date_str or date_str.lower() in ['nil', 'null', '']:
        return None
    # Try various formats
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y', '%d-%b-%Y'):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    # If none worked, return None
    return None

def build_link(item):
    """Build the link URL based on item data."""
    link = item.get('link', '').strip()
    link_address = item.get('link_address', '').strip()
    file_path = item.get('file_path', '').strip()
    
    # Prefer link if it looks like a URL
    if link and (link.startswith('http://') or link.startswith('https://')):
        return link
    if link_address and (link_address.startswith('http://') or link_address.startswith('https://')):
        return link_address
    
    # If link is a relative path, construct absolute URL
    if link and not link.startswith('http'):
        # Remove leading slash if present
        if link.startswith('/'):
            link = link[1:]
        return f'https://k2image.85200852.xyz/{link}'
    if link_address and not link_address.startswith('http'):
        if link_address.startswith('/'):
            link_address = link_address[1:]
        return f'https://k2image.85200852.xyz/{link_address}'
    if file_path and not file_path.startswith('http'):
        if file_path.startswith('/'):
            file_path = file_path[1:]
        return f'https://k2image.85200852.xyz/{file_path}'
    
    return ''  # No valid link

def is_valid_link(link):
    """Check if link is valid and not a placeholder."""
    if not link or link.strip() == '':
        return False
    lower_link = link.lower()
    if 'missing' in lower_link or 'nil' in lower_link or 'null' in lower_link:
        return False
    return True

def get_primary_secondary_category(item, filename):
    """Determine primary and secondary category based on rules."""
    category = item.get('category', '').strip()
    section = item.get('Section', item.get('section', '')).strip()
    title = item.get('title', '').strip()
    method = item.get('method', '').strip()
    
    # Check for GB/BS
    if 'GB' in category.upper() or 'BS' in category.upper():
        primary = '標準規格'
        secondary = 'GB' if 'GB' in category.upper() else 'BS'
        return primary, secondary
    
    # Check for Method or Section == 'Method'
    if section == 'Method' or 'Method' in category or 'Method' in section:
        primary = '施工做法'
        secondary = 'MSF'  # default, could be refined from method or section
        # Try to extract something like MSF from method or section
        if section:
            secondary = section.split()[0] if section else 'MSF'
        return primary, secondary
    
    # Check for Gov_B or Gov_C from filename
    filename_lower = filename.lower()
    if 'gov_b' in filename_lower:
        primary = '政府圖紙'
        secondary = 'Gov_B'
        return primary, secondary
    if 'gov_c' in filename_lower:
        primary = '政府圖紙'
        secondary = 'Gov_C'
        return primary, secondary
    
    # Default to StandardSpec (treat as 標準規格)
    primary = '標準規格'
    # Try to get secondary from category or title
    if category:
        secondary = category.split()[0] if category else 'Standard'
    else:
        secondary = 'Standard'
    return primary, secondary

def process_json_file(json_path):
    """Process a single JSON file and yield markdown frontmatter and content."""
    filename = json_path.name
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  Error parsing {filename}: {e}")
        return
    
    if not isinstance(data, list):
        print(f"  Warning: {filename} does not contain a list, skipping.")
        return
    
    for item in data:
        if not isinstance(item, dict):
            continue
        
        # Get title (prefer title_c, else title)
        title = item.get('title_c', '').strip() or item.get('title', '').strip()
        if not title:
            # Skip items without title
            continue
        
        # Get date
        date_str = item.get('date', '')
        date = extract_date(date_str)
        if not date:
            # Try to get from file modification time as fallback
            mtime = json_path.stat().st_mtime
            date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        
        # Get categories
        primary, secondary = get_primary_secondary_category(item, filename)
        categories = [primary, secondary]
        
        # Get tags
        tags_str = item.get('tags', '')
        tags = [t.strip() for t in tags_str.split(',') if t.strip()] if isinstance(tags_str, str) else []
        # If tags is empty, try to get from method or category?
        if not tags:
            method = item.get('method', '')
            if method:
                tags = [method]
        
        # Get uid
        uid = item.get('id', '').strip()
        if not uid:
            # Try to generate from title and date
            uid = f"{date}-{title}".lower().replace(' ', '-')
        
        # Get link
        link = build_link(item)
        if not is_valid_link(link):
            link = ''  # We'll leave it empty in frontmatter
        
        # Get description
        description = item.get('description', '').strip()
        if not description or description.lower() in ['nil', 'null']:
            description = ''
        
        # Build frontmatter
        frontmatter = []
        frontmatter.append('---')
        frontmatter.append(f'title: "{title}"')
        frontmatter.append(f'date: {date}')
        frontmatter.append(f'categories: [{", ".join(categories)}]')
        if tags:
            tags_str = ', '.join([f'"{t}"' for t in tags])
            frontmatter.append(f'tags: [{tags_str}]')
        if uid:
            frontmatter.append(f'uid: "{uid}"')
        if link:
            frontmatter.append(f'link: "{link}"')
        frontmatter.append('---')
        frontmatter.append('')  # empty line
        
        # Add description as first paragraph if available
        if description:
            frontmatter.append(description)
            frontmatter.append('')  # empty line after description
        
        yield '\n'.join(frontmatter)

def main():
    """Main processing function."""
    # Collect all entries, deduplicate by uid (keeping latest date)
    entries_by_uid = {}  # uid -> {date, markdown, title}
    
    json_files = list(SOURCE_DIR.glob('*.json'))
    print(f"Found {len(json_files)} JSON files to process.")
    
    for json_file in json_files:
        print(f"Processing {json_file.name}...")
        for markdown in process_json_file(json_file):
            # Extract uid from the markdown frontmatter (simple parsing)
            # We'll parse the uid from the markdown string
            uid = None
            date = None
            title = None
            for line in markdown.split('\n'):
                if line.startswith('uid:'):
                    uid = line.split('"')[1] if '"' in line else line.split(':')[1].strip()
                elif line.startswith('date:'):
                    date = line.split(':')[1].strip()
                elif line.startswith('title:'):
                    title = line.split('"')[1] if '"' in line else line.split(':')[1].strip()
            
            if not uid:
                # If we can't extract uid, skip deduplication and use a hash of the markdown
                uid = hash(markdown)  # not ideal but better than nothing
            
            # Keep the entry with the latest date
            if uid in entries_by_uid:
                if date > entries_by_uid[uid]['date']:
                    entries_by_uid[uid] = {
                        'date': date,
                        'markdown': markdown,
                        'title': title
                    }
            else:
                entries_by_uid[uid] = {
                    'date': date,
                    'markdown': markdown,
                    'title': title
                }
    
    print(f"Found {len(entries_by_uid)} unique entries after deduplication.")
    
    # Write markdown files
    written = 0
    for uid, info in entries_by_uid.items():
        # Create a safe filename from title and date
        safe_title = re.sub(r'[^\w\s-]', '', info['title']).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        # Limit length to avoid filesystem issues
        if len(safe_title) > 100:
            safe_title = safe_title[:100].rstrip('-')
        if not safe_title:
            safe_title = uid
        
        date_str = info['date']
        filename = f'{date_str}-{safe_title}.md'
        filepath = TARGET_DIR / filename
        
        # Avoid overwriting by adding a counter if needed
        counter = 1
        while filepath.exists():
            filename = f'{date_str}-{safe_title}-{counter}.md'
            filepath = TARGET_DIR / filename
            counter += 1
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(info['markdown'])
            written += 1
            print(f'  Written: {filename}')
        except Exception as e:
            print(f'  Error writing {filename}: {e}')
    
    print(f'Successfully wrote {written} markdown files to {TARGET_DIR}')
    
    # Run hexo generate
    print('Running hexo generate...')
    blog_dir = TARGET_DIR.parent.parent  # /tmp/blog-content
    os.chdir(blog_dir)
    result = os.system('npx hexo generate')
    if result == 0:
        print('Hexo generate completed successfully.')
    else:
        print(f'Hexo generate failed with exit code {result}')
    
    # Copy public folder to /var/www/blog/ (simulate)
    public_dir = blog_dir / 'public'
    target_blog = Path('/var/www/blog')
    if public_dir.exists():
        print(f'Copying {public_dir} to {target_blog}...')
        try:
            if target_blog.exists():
                shutil.rmtree(target_blog)
            shutil.copytree(public_dir, target_blog)
            print('Copy completed.')
        except Exception as e:
            print(f'Error copying: {e}')
    else:
        print('Public directory not found, skipping copy.')

if __name__ == '__main__':
    main()
