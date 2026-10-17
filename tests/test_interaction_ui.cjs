// Controller unit tests with no browser or network. Layout/click acceptance is separate.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function deferred() {
  let resolve;
  const promise = new Promise(done => resolve = done);
  return {promise, resolve};
}
function care(patch={}) {
  return {enabled:false,touch_enabled:true,effects_enabled:true,
    satiety:80,hydration:80,mood:80,feed_wait:0,drink_wait:0,...patch};
}
function harness() {
  const elements = new Map(), fetches = [], urls = [], revoked = [];
  const documentEvents = {}, windowEvents = {};
  function element(key) {
    if (!elements.has(key)) {
      const classes = new Set();
      elements.set(key, {disabled:false,hidden:false,textContent:'',src:'',events:{},attrs:{},
        classList:{add:v=>classes.add(v),remove:v=>classes.delete(v),
          toggle:(v,on)=>on ? classes.add(v) : classes.delete(v)},
        addEventListener(name, handler) { this.events[name] = handler; },
        setAttribute(name,value) { this.attrs[name] = value; },
        decode:async () => {},
        getBoundingClientRect:() => ({left:0,top:0,width:256,height:384})});
    }
    return elements.get(key);
  }
  const form = element('#interaction-form');
  form.elements = {enabled:{checked:false},touch_enabled:{checked:true},effects_enabled:{checked:true}};
  const previews = ['pet','poke','nod','shake','dance','lift','feed','drink'].map(action => {
    const button = element('preview-'+action); button.dataset = {preview:action}; return button;
  });
  const feeds = ['feed','drink'].map(action => {
    const button = element('care-'+action); button.dataset = {care:action}; return button;
  });
  const media = {matches:false,addEventListener:() => {}};
  const context = vm.createContext({
    $:selector => selector === 'input[name="preview_strength"]:checked' ? {value:'lively'} : element(selector),
    $$:selector => selector === '[data-preview]' ? previews : selector === '[data-care]' ? feeds : [],
    state:{settings:{skin:'default'},interaction:care()},token:'UNIT_TEST_ONLY',
    matchMedia:() => media,AbortController,URLSearchParams,
    URL:{createObjectURL:blob => {const url='blob:unit-'+urls.length; urls.push({url,blob}); return url;},
      revokeObjectURL:url => revoked.push(url)},
    document:{hidden:false,addEventListener:(name,handler) => documentEvents[name]=handler},
    window:{addEventListener:(name,handler) => windowEvents[name]=handler},
    setTimeout:() => 1,clearTimeout:() => {},setInterval:() => 1,
    toast:() => {},
    api:async () => {throw new Error('Unexpected API call');},
    fetch:(url, options) => {const request=deferred(); fetches.push({url,options,...request}); return request.promise;}
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../control-ui/interaction.js'),'utf8'),context);
  context.renderInteraction(context.state.interaction);
  return {context,element,form,fetches,urls,revoked,feeds,media,documentEvents,windowEvents};
}
function response(blob) { return {ok:true,blob:async () => blob}; }

test('a stopped preview cannot reappear when its old fetch finishes',async () => {
  const h=harness();
  const play=h.context.previewAnimation('dance');
  h.context.stopInteractionPreview('Stopped');
  h.fetches[0].resolve(response('old dance'));
  await play;
  assert.equal(h.urls.length,0);
  assert.equal(h.element('#interaction-preview-status').textContent,'Stopped');
  assert.match(h.element('#interaction-preview').src,/curious\.png$/);
});

test('a slower previous action cannot replace the latest selected action',async () => {
  const h=harness();
  const first=h.context.previewAnimation('pet');
  const second=h.context.previewAnimation('nod');
  h.fetches[1].resolve(response('new nod')); await second;
  h.fetches[0].resolve(response('old pet')); await first;
  assert.equal(h.urls.length,1);
  assert.equal(h.urls[0].blob,'new nod');
  assert.equal(h.element('#interaction-preview-status').textContent,'正在试映：点点头');
  h.documentEvents['nijika:page']({detail:'skins'});
  assert.deepEqual(h.revoked,['blob:unit-0']);
  assert.match(h.element('#interaction-preview').src,/curious\.png$/);
});

test('polling and a save response preserve edits made while saving',async () => {
  const h=harness(), saved=deferred();
  h.form.elements.enabled.checked=true;
  h.form.events.change({target:{name:'enabled'}});
  h.context.renderInteraction(care());
  assert.equal(h.form.elements.enabled.checked,true);
  h.context.api=() => saved.promise;
  const submission=h.form.events.submit({preventDefault:() => {}});
  h.form.elements.enabled.checked=false;
  h.form.events.change({target:{name:'enabled'}});
  saved.resolve(care({enabled:true})); await submission;
  assert.equal(h.form.elements.enabled.checked,false);
  assert.equal(h.element('#interaction-save-status').textContent,'有未保存的修改');
  assert.equal(h.element('#save-interaction').disabled,false);
  assert.equal(h.element('#feed-pet').disabled,true);
});

test('a successful feed is preserved even if its decorative preview fails',async () => {
  const h=harness();
  h.context.state.interaction=care({enabled:true});
  h.context.renderInteraction(h.context.state.interaction);
  h.context.api=async () => ({action:'feed',care:care({enabled:true,satiety:100,mood:84,feed_wait:30})});
  await h.feeds[0].events.click();
  assert.equal(h.context.state.interaction.satiety,100);
  assert.match(h.element('#care-result').textContent,/点心收到/);
  assert.equal(h.element('#feed-pet').disabled,true);
  h.fetches[0].resolve({ok:false,json:async () => ({error:'preview unavailable'})});
  await new Promise(resolve => setImmediate(resolve));
  assert.match(h.element('#interaction-preview-status').textContent,/preview unavailable/);
  assert.match(h.element('#care-result').textContent,/点心收到/);
});

test('reduced motion avoids animation fetches and touch disabling keeps action buttons usable',async () => {
  const h=harness(); h.media.matches=true;
  await h.context.previewAnimation('shake');
  assert.equal(h.fetches.length,0);
  assert.match(h.element('#interaction-preview').src,/wink\.png$/);
  h.form.elements.touch_enabled.checked=false;
  h.element('#interaction-character').events.click({currentTarget:h.element('#interaction-character'),clientX:100,clientY:40,detail:1});
  assert.match(h.element('#interaction-preview-status').textContent,/分区触摸已关闭/);
  await h.context.previewAnimation('pet');
  assert.match(h.element('#interaction-preview-status').textContent,/静态表情/);
});
