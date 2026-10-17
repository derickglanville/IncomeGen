import assert from 'node:assert/strict';
import fs from 'node:fs';

const html=fs.readFileSync(new URL('../docs/index.html',import.meta.url),'utf8');
const js=fs.readFileSync(new URL('../docs/app.js',import.meta.url),'utf8');
const manifest=JSON.parse(fs.readFileSync(new URL('../docs/manifest.json',import.meta.url),'utf8'));
assert.match(html,/Continue with Google/);
assert.match(html,/viewport-fit=cover/);
assert.match(js,/incomegen\/workspace/);
assert.match(js,/dglanville@gmail\.com/);
// Role entries plus one platform-registry entry for each provider.
assert.equal((js.match(/\['Mercor'/g)||[]).length,20);
assert.equal((js.match(/\['Outlier'/g)||[]).length,7);
assert.equal(manifest.display,'standalone');
assert.doesNotMatch(js,/sqlite/i);
console.log('IncomeGen static Firebase checks passed.');
