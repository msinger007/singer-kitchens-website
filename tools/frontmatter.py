"""Read/write the JSON front matter used by src/pages/*.njk and src/posts/*.md."""
import json


def load(path):
    s = open(path, encoding='utf-8').read()
    assert s.startswith('---json\n'), path
    end = s.index('\n---\n', 8)
    return json.loads(s[8:end]), s[end + 5:]


def save(path, fm, body):
    open(path, 'w', encoding='utf-8').write('---json\n' + json.dumps(fm, indent=2, ensure_ascii=False) + '\n---\n' + body)
