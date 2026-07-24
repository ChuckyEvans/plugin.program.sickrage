import difflib
bk = r"backups\\20260714-182936"
files = ["util.py","settingsMenu.py"]
for fn in files:
    a_path = bk + '\\' + fn + '.bak'
    b_path = 'resources\\lib\\' + fn
    try:
        with open(a_path, 'r', encoding='utf-8') as f:
            a = f.read().splitlines()
        with open(b_path, 'r', encoding='utf-8') as f:
            b = f.read().splitlines()
    except Exception as e:
        print(f'Error reading {fn}: {e}')
        continue
    diff = list(difflib.unified_diff(a,b,fromfile=a_path,tofile=b_path,lineterm=''))
    print('\n' + '='*80)
    print(f'DIFF for {fn} (backup -> restored)')
    print('='*80)
    if diff:
        for line in diff[:500]:
            print(line)
        if len(diff) > 500:
            print('... (diff truncated)')
    else:
        print('(no differences)')
