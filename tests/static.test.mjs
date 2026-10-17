import assert from 'node:assert/strict';
import fs from 'node:fs';

const html=fs.readFileSync(new URL('../docs/index.html',import.meta.url),'utf8');
const js=fs.readFileSync(new URL('../docs/app.js',import.meta.url),'utf8');
const manifest=JSON.parse(fs.readFileSync(new URL('../docs/manifest.json',import.meta.url),'utf8'));
const rules=fs.readFileSync(new URL('../firestore.rules',import.meta.url),'utf8');
assert.match(html,/Continue with Google/);
assert.match(html,/viewport-fit=cover/);
assert.match(js,/incomegen\/workspace/);
assert.match(js,/dglanville@gmail\.com/);
// Role entries plus one platform-registry entry for each provider.
assert.equal((js.match(/\['Mercor'/g)||[]).length,20);
assert.equal((js.match(/\['Outlier'/g)||[]).length,7);
assert.equal(manifest.display,'standalone');
assert.doesNotMatch(js,/sqlite/i);
for(const collection of ['food_tracker_meals','food_tracker_health','food_tracker_wellness','stenotype_users','theo_job_search','incomegen','solar_daily_entries','solar_tracker_config','tracker_refresh_signals','tracker_state'])assert.match(rules,new RegExp('match /'+collection.replace('/','\\/')));
assert.match(rules,/match \/incomegen\/\{documentId\}/);
assert.match(rules,/request\.auth\.token\.email == 'dglanville@gmail\.com'/);
console.log('IncomeGen static Firebase checks passed.');
