import pathlib

path = pathlib.Path(r"""C:\Users\rseba\Projects\Field_Guide_App\.claude\plans\parts\2026-03-30-wiring-routing-audit-fixes-part1.md""" )

# Read template content from the companion .txt file
txt_path = path.with_suffix('.txt')
content = txt_path.read_text(encoding='utf-8')
path.write_text(content, encoding='utf-8')
print(f'Wrote {len(content)} chars to plan file')
