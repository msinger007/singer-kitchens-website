#!/usr/bin/env python3
"""Undo LF -> CRLF corruption in the Drive download of wp-content/uploads.

The uploads zip from Drive arrived with every 0x0A byte turned into 0x0D 0x0A (a text-mode
transfer). A genuine binary file almost always contains lone 0x0A bytes; a corrupted one has
none. For files with CRLF pairs and no lone LF, replacing CRLF with LF restores the original.
Usage: python3 tools/repair_uploads.py source/uploads
"""
import os, sys, json
root = sys.argv[1]
fixed = []
for r, ds, fs in os.walk(root):
    for f in fs:
        if f.lower().rsplit('.', 1)[-1] in ('svg', 'txt', 'css', 'js', 'json', 'html', 'htm', 'xml', 'csv', 'md', 'log'):
            continue
        p = os.path.join(r, f)
        b = open(p, 'rb').read()
        crlf = b.count(b'\r\n')
        if crlf and b.count(b'\n') == crlf :
            open(p, 'wb').write(b.replace(b'\r\n', b'\n'))
            fixed.append(os.path.relpath(p, root))
print(len(fixed), 'files repaired')
out = os.path.join(os.path.dirname(__file__), '..', 'reports', 'repaired-uploads.json')
prev = json.load(open(out)) if os.path.exists(out) else []
json.dump(sorted(set(prev) | set(fixed)), open(out, 'w'), indent=0)
