// Fallback form filler for a bestpractices.dev edit page (…/projects/<id>/<level>/edit).
// Prefer proposal URLs (badge.py urls); use this only when they don't work.
//
// Run with Claude in Chrome's javascript_tool on the edit page: paste this file, then one call,
// e.g.  osb.fill(<output of `badge.py payload answers.yaml --keys a,b,c`>)
// The page reloads after saving, so paste the file again before osb.remaining().
//
// Results hold criterion keys and counts only. Claude in Chrome blocks output that contains
// URLs or query strings, and truncates it at about 1,000 characters.
window.osb = (() => {
  const form = () => document.querySelector('form[id^=edit_project]');
  const short = (list, max = 40) => (list.length > max ? [...list.slice(0, max), `+${list.length - max} more`] : list);

  // answers: {key: [status, justification]}; status is Met, Unmet, N/A or ?
  const fill = (answers) => {
    const f = form();
    if (!f) return { error: 'no edit form here; open the /edit page (the page without /edit is read-only)' };
    const problems = [];
    let filled = 0;
    for (const [key, [status, justification]] of Object.entries(answers)) {
      const radio = f.querySelector(`input[name="project[${key}_status]"][value="${status}"]`);
      if (!radio) {
        problems.push(`no ${status} option: ${key}`); // e.g. N/A doesn't exist for this criterion
        continue;
      }
      radio.click();
      const text = f.querySelector(`[name="project[${key}_justification]"]`);
      if (text) {
        text.value = justification;
        text.dispatchEvent(new Event('input', { bubbles: true }));
      } else {
        problems.push(`no justification box: ${key}`);
      }
      filled += 1;
    }
    return { filled, problems: short(problems) };
  };

  // "Save (and continue)": saves and stays on the page. Only after the user's go-ahead.
  const save = () => {
    const f = form();
    const button = f && [...f.querySelectorAll('[type=submit]')].find((b) => b.name === 'continue' && b.value === 'Save');
    if (!button) return { error: 'no Save button found' };
    button.click();
    return { clicked: 'Save' };
  };

  // What still keeps the badge back, after a save and reload.
  const remaining = () => {
    const f = form();
    if (!f) return { error: 'no edit form here' };
    const names = new Set([...f.querySelectorAll('input[type=radio][name$="_status]"]')].map((r) => r.name));
    const open = [];
    for (const name of names) {
      const checked = f.querySelector(`input[name="${name}"]:checked`);
      const value = checked ? checked.value : 'none';
      if (value !== 'Met' && value !== 'N/A') open.push(`${name.slice(8, -8)}=${value}`);
    }
    // Met chosen, but the required URL or justification is missing.
    const notEnough = [...document.querySelectorAll('img[alt*="not enough" i]')].map((img) => {
      const holder = img.closest('[id]');
      return holder ? holder.id : '?';
    });
    const text = document.body.innerText;
    const automationDisagrees = (text.match(/Automation instead determined/g) || []).length;
    const flash = document.querySelector('.alert, .flash, #notice, #flash');
    return {
      notMetOrNA: short(open),
      notEnough: short(notEnough),
      automationDisagrees,
      flash: flash ? flash.innerText.trim().slice(0, 120) : '',
    };
  };

  return { fill, save, remaining };
})();
// An assignment, so the tool prints this line as the result of the paste.
window.osb.ready = 'osb ready: osb.fill(answers), osb.save(), osb.remaining()';
