import html
import json
import re

with open('pravki.html', encoding='utf-8') as f:
    src = f.read()

file_re = re.compile(r'<span class="source-tree__file-name">([^<]+)</span>')
comment_re = re.compile(
    r'source-tree__comment-markdown">(.*?)<div class="source-tree__comment-info"',
    re.DOTALL,
)
status_re = re.compile(
    r'comment-info-status_type_(\w+)"[^>]*>\s*<span>([^<]*)</span>'
)

folder_re = re.compile(r'<span class="source-tree__folder-name">([^<]+)</span>')

events = []
last_folder = [None]
for m in folder_re.finditer(src):
    events.append((m.start(), 'folder', m.group(1)))
for m in file_re.finditer(src):
    events.append((m.start(), 'file', m.group(1)))
for m in comment_re.finditer(src):
    body = m.group(1)
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', body, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</(p|div|li|h\d|blockquote)>', '\n', text)
    text = re.sub(r'<li[^>]*>', '- ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text).strip()

    sm = status_re.search(body + '<div class="source-tree__comment-info"')
    tail = src[m.end():m.end() + 400]
    sm = status_re.search(tail)
    status = sm.group(2) if sm else '?'
    sev = {'Отлично': 'good', 'Можно лучше': 'warning', 'Надо исправить': 'critical'}.get(status, sm.group(1) if sm else '?')
    events.append((m.start(), 'comment', {'file': None, 'status': status, 'severity': sev, 'text': text}))

events.sort(key=lambda e: e[0])

comments = []
cur_file = None
cur_folder = None
for pos, kind, val in events:
    if kind == 'folder':
        cur_folder = val
    elif kind == 'file':
        cur_file = val
    else:
        val['folder'] = cur_folder
        val['file'] = f"{cur_folder}/{cur_file}" if cur_folder else cur_file
        comments.append(val)

by_sev = {'critical': [], 'warning': [], 'good': []}
for i, c in enumerate(comments, 1):
    by_sev[c['severity']].append((i, c))

with open('pravki_extracted.json', 'w', encoding='utf-8') as f:
    json.dump(comments, f, ensure_ascii=False, indent=2)

with open('pravki_extracted.md', 'w', encoding='utf-8') as f:
    f.write(f"# Комментарии ревьюера (всего: {len(comments)})\n\n")
    for sev, title in (('critical', 'НАДО ИСПРАВИТЬ'), ('warning', 'МОЖНО ЛУЧШЕ'), ('good', 'ОТЛИЧНО')):
        f.write(f"## {title} ({len(by_sev[sev])})\n\n")
        for i, c in by_sev[sev]:
            f.write(f"### #{i} [{c['status']}] файл: {c['file']}\n\n{c['text']}\n\n---\n\n")

print('total:', len(comments))
print('critical:', len(by_sev['critical']))
print('warning:', len(by_sev['warning']))
print('good:', len(by_sev['good']))
