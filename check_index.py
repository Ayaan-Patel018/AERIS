c = open('index.html', encoding='utf-8').read()
items = [
    ('AERIS title', 'AERIS' in c),
    ('Side rail nav', 'class="rail"' in c),
    ('Top-bar', 'class="top-bar"' in c),
    ('Hero section', 'id="overview"' in c),
    ('Grid cells', 'class="gc' in c),
    ('Grid nodes gc::after', 'gc::after' in c),
    ('Problem section', 'id="problem"' in c),
    ('5 solution steps', c.count('class="step"') == 5),
    ('Demo section', 'id="proof"' in c),
    ('Map canvas', 'id="mapCanvas"' in c),
    ('Timeline', 'class="tl-row"' in c),
    ('Architecture', 'id="tech"' in c),
    ('Arch modal', 'class="amodal"' in c),
    ('Particle canvas', 'heroCanvas' in c),
    ('Rail progress', 'railProg' in c),
]
for name, ok in items:
    status = 'OK  ' if ok else 'FAIL'
    print(status + ' ' + name)
print('Total size: ' + str(len(c)) + ' bytes')
