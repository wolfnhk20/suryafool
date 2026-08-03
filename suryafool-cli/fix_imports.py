import os

for root, dirs, files in os.walk(r'F:\projects\suryafool\suryafool-cli\src'):
    for f in files:
        if f.endswith('.js'):
            p = os.path.join(root, f)
            with open(p, 'r') as fh:
                content = fh.read()
            content = content.replace('.jsx', '.js')
            with open(p, 'w') as fh:
                fh.write(content)
            print(f'Fixed imports in {p}')