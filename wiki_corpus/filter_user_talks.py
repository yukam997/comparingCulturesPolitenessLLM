import json
import bz2
import xml.etree.ElementTree as ET

NS = {'mw': 'http://www.mediawiki.org/xml/export-0.11/'}

def extract_simple(dump_file, output_file='user_talks_simple_ja.jsonl.bz2', max_pages=None):
    """Extract user talk pages WITHOUT parsing conversation structure"""
    
    count = 0
    with bz2.open(dump_file, 'rt', encoding='utf-8') as f_in, \
         bz2.open(output_file, 'wt', encoding='utf-8') as f_out:
        
        for event, elem in ET.iterparse(f_in, events=('end',)):
            if elem.tag == '{http://www.mediawiki.org/xml/export-0.11/}page':
                ns = elem.find('mw:ns', NS)
                
                if ns is not None and ns.text == '3':
                    count += 1
                    if max_pages and count > max_pages:
                        break
                    
                    title = elem.find('mw:title', NS)
                    page_id = elem.find('mw:id', NS)
                    revision = elem.find('mw:revision', NS)
                    
                    if revision is not None:
                        text_elem = revision.find('mw:text', NS)
                        timestamp = revision.find('mw:timestamp', NS)
                        contributor = revision.find('mw:contributor', NS)
                        
                        username = None
                        if contributor is not None:
                            username_elem = contributor.find('mw:username', NS)
                            username = username_elem.text if username_elem is not None else None
                        
                        # Simple record - just the raw text
                        record = {
                            'page_id': page_id.text if page_id is not None else None,
                            'title': title.text if title is not None else None,
                            'timestamp': timestamp.text if timestamp is not None else None,
                            'last_editor': username,
                            'text': text_elem.text if text_elem is not None else None
                        }
                        
                        # Write without parsing structure
                        f_out.write(json.dumps(record, ensure_ascii=False) + '\n')
                    
                    if count % 1000 == 0:
                        print(f"Processed {count} pages...")
                
                elem.clear()
    
    print(f"Extracted {count} pages to {output_file}")

# Usage
extract_simple('jawiki-latest-pages-meta-current1.xml-p1p114794.bz2',
               'user_talks_simple_ja.jsonl.bz2',)