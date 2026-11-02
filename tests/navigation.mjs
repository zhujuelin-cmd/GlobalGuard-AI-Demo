import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {JSDOM, VirtualConsole} from 'jsdom';
const root = new URL('../', import.meta.url);
const source = await readFile(new URL('landing.js', root), 'utf8');
const built = await readFile(new URL('dist/index.html', root), 'utf8');
assert.ok(built.includes(source), 'built bundle must contain current landing source verbatim');
// Reconstitute the source entry point, inlining only for the test srcdoc harness.
let entry = await readFile(new URL('index.html', root), 'utf8');
for (const name of ['data-engine.js', 'landing.js']) {
  entry = entry.replace(`<script src="${name}"></script>`, `<script>\n${await readFile(new URL(name, root), 'utf8')}\n</script>`);
}
let checks = 1;
for (const [label, html] of [['source', entry], ['built', built]]) {
  for (const url of ['about:srcdoc', 'https://globalguard.test/demo?mode=1']) {
    const errors = [];
    const vc = new VirtualConsole();
    vc.on('jsdomError', e => errors.push(e.message));
    const dom = new JSDOM(html, {url, runScripts:'dangerously', pretendToBeVisual:true, virtualConsole:vc,
      beforeParse(w) {
        w.scrollTo = () => {};
        w.HTMLElement.prototype.scrollIntoView = () => {};
        w.matchMedia = () => ({matches:true});
      }
    });
    const w = dom.window, d = w.document;
    const original = w.history.pushState.bind(w.history);
    let calls = 0;
    if (url.startsWith('about:')) {
      assert.throws(() => original({page:'dashboard'}, '', w.location.pathname+w.location.search+'#dashboard'), {name:'SecurityError'});
      checks++;
    }
    w.history.pushState = (...args) => {calls++; return original(...args);};
    await w.enterEngine('risk');
    assert.equal(d.getElementById('landingPage').hidden, true);
    assert.equal(d.getElementById('dashboardShell').hidden, false);
    assert.equal(d.getElementById('engineTransition').hidden, true);
    assert.equal(w.eval('landingBusy'), false);
    assert.equal(w.eval('s.data.topic'), 'eco');
    assert.equal(d.activeElement.id, 'homeBtn');
    w.showLanding();
    assert.equal(d.getElementById('landingPage').hidden, false);
    assert.equal(d.getElementById('dashboardShell').hidden, true);
    assert.equal(calls, url.startsWith('about:') ? 0 : 2);
    if (!url.startsWith('about:')) {
      assert.equal(w.location.href, 'https://globalguard.test/demo?mode=1#home');
      const unrelated = new TypeError('unrelated history failure');
      w.history.pushState = () => {throw unrelated;};
      assert.throws(() => w.pushPageHistory('dashboard'), e => e === unrelated);
      checks += 2;
    } else {
      assert.equal(w.location.href, 'about:srcdoc');
      checks++;
    }
    assert.deepEqual(errors, [], label+' runtime errors');
    checks += 10;
    dom.window.close();
  }
}
console.log(`PASS: ${checks} navigation/source-to-bundle checks; srcdoc SecurityError reproduced and avoided; HTTPS history and unrelated error propagation verified.`);
