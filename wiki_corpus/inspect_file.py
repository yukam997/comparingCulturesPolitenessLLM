import xml.etree.ElementTree as ET
import bz2
def extract_user_talk(dump_file):
    count=0
    quite_count=0
    with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
        for event, elem in ET.iterparse(f, events=('end',)):
            # extract export version
            if elem.tag == '{http://www.mediawiki.org/xml/export-0.11/}page':
                ns = elem.find('{http://www.mediawiki.org/xml/export-0.11/}ns')
                title = elem.find('{http://www.mediawiki.org/xml/export-0.11/}title')
                text = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}text')
                if ns is not None and ns.text == '3':
                    try:
                        print(f"Title: {title.text}")
                        # print(f"Text: {text.text[:500]}...")x
                        print("-" * 80)
                        if "quite" in text.text:
                            print("Found 'quite' in title")
                            quite_count += 1
                        count += 1
                    except:
                       print("text or title is empty")

                elem.clear()


    return count, quite_count

# Usage
count, quite_count = extract_user_talk('./enwiki-latest-pages-meta-current10.xml-p4045403p5399366.bz2')
print(f"Total pages processed: {count}")
print(f"Total 'quite' found: {quite_count}")