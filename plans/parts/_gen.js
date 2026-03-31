
const fs = require('fs');
const path = 'C:/Users/rseba/Projects/Field_Guide_App/.claude/plans/parts/2026-03-30-wiring-routing-audit-fixes-part1.md';

// We read the content from a .txt template
const tmpl = 'C:/Users/rseba/Projects/Field_Guide_App/.claude/plans/parts/_part1.txt';
const content = fs.readFileSync(tmpl, 'utf8');
fs.writeFileSync(path, content);
console.log('Wrote ' + content.length + ' chars');
