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
  const decodeQueue = [], preloads = [];
  const documentEvents = {}, windowEvents = {};
  function makeElement(key, previousClasses=[]) {
    const classes = new Set(previousClasses);
    return {disabled:false,hidden:false,textContent:'',src:'',events:{},attrs:{},dataset:{},
      classList:{add:v=>classes.add(v),remove:v=>classes.delete(v),contains:v=>classes.has(v),
        toggle:(v,on)=>on ? classes.add(v) : classes.delete(v)},
      addEventListener(name, handler) { this.events[name] = handler; },
      scrollIntoView(options) { this.scrolled = options; },
      setAttribute(name,value) { this.attrs[name] = value; },
      decode:() => decodeQueue.shift()?.promise || Promise.resolve(),
      cloneNode() { const image=makeElement(key,classes); preloads.push(image); return image; },
      replaceWith(replacement) { elements.set(key,replacement); },
      getBoundingClientRect:() => ({left:0,top:0,width:256,height:384})};
  }
  function element(key) {
    if (!elements.has(key)) {
      elements.set(key,makeElement(key));
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
  return {context,element,form,fetches,urls,revoked,feeds,media,documentEvents,windowEvents,decodeQueue,preloads};
}
function response(blob) { return {ok:true,blob:async () => blob}; }

test('the visible animation stays in place until its replacement has decoded',async () => {
  const h=harness();
  const first=h.context.previewAnimation('pet');
  h.fetches[0].resolve(response('first')); await first;
  const shown=h.element('#interaction-preview'), gate=deferred();
  h.decodeQueue.push(gate);
  const second=h.context.previewAnimation('nod');
  assert.equal(h.element('#interaction-preview'),shown);
  assert.equal(shown.src,'blob:unit-0');
  h.fetches[1].resolve(response('next'));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(h.element('#interaction-preview'),shown);
  assert.equal(h.element('.interaction-stage').attrs['aria-busy'],'true');
  assert.deepEqual(h.revoked,[]);
  gate.resolve(); await second;
  assert.notEqual(h.element('#interaction-preview'),shown);
  assert.equal(h.element('#interaction-preview').src,'blob:unit-1');
  assert.equal(h.element('.interaction-stage').attrs['aria-busy'],'false');
  assert.deepEqual(h.revoked,['blob:unit-0']);
});

test('a stopped decode cannot publish its image and releases the unused URL',async () => {
  const h=harness(), gate=deferred(); h.decodeQueue.push(gate);
  const playing=h.context.previewAnimation('dance');
  h.fetches[0].resolve(response('late decoded dance'));
  await new Promise(resolve=>setImmediate(resolve));
  h.context.stopInteractionPreview('Stopped while decoding');
  const stopped=h.element('#interaction-preview');
  gate.resolve(); await playing;
  assert.equal(h.element('#interaction-preview'),stopped);
  assert.match(stopped.src,/curious\.png$/);
  assert.deepEqual(h.revoked,['blob:unit-0']);
  assert.equal(h.element('#interaction-preview-status').textContent,'Stopped while decoding');
});

test('a failed next request leaves the already displayed animation visible',async () => {
  const h=harness();
  const first=h.context.previewAnimation('pet');
  h.fetches[0].resolve(response('shown')); await first;
  const shown=h.element('#interaction-preview');
  const second=h.context.previewAnimation('nod');
  h.fetches[1].resolve({ok:false,json:async()=>({error:'try later'})}); await second;
  assert.equal(h.element('#interaction-preview'),shown);
  assert.equal(shown.src,'blob:unit-0');
  assert.deepEqual(h.revoked,[]);
  assert.match(h.element('#interaction-preview-status').textContent,/try later/);
});

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

test('reverting interaction switches clears the draft and re-enables care', () => {
  const h=harness();
  h.context.state.interaction=care({enabled:true});
  h.context.renderInteraction(h.context.state.interaction);
  h.form.elements.effects_enabled.checked=false;
  h.form.events.change({target:{name:'effects_enabled'}});
  assert.equal(h.element('#feed-pet').disabled,true);
  h.form.elements.effects_enabled.checked=true;
  h.form.events.change({target:{name:'effects_enabled'}});
  assert.equal(h.element('#save-interaction').disabled,true);
  assert.equal(h.element('#feed-pet').disabled,false);
  assert.equal(h.form.dataset.saveState,'saved');
});

test('polling cannot overwrite a reverted draft while its save is pending',async () => {
  const h=harness(), saved=deferred();
  h.form.elements.enabled.checked=true;
  h.form.events.change({target:{name:'enabled'}});
  h.context.api=() => saved.promise;
  const submission=h.form.events.submit({preventDefault:() => {}});
  h.form.elements.enabled.checked=false;
  h.form.events.change({target:{name:'enabled'}});
  h.context.renderInteraction(care({enabled:true,effects_enabled:false}));
  assert.equal(h.form.elements.enabled.checked,false);
  assert.equal(h.form.elements.effects_enabled.checked,true);
  saved.resolve(care({enabled:true}));
  await submission;
  assert.equal(h.form.elements.enabled.checked,false);
  assert.equal(h.form.dataset.saveState,'dirty');
  assert.equal(h.form.attrs['aria-busy'],'false');
});

test('failed interaction saves keep their error across polling and permit retry',async () => {
  const h=harness();
  h.form.elements.enabled.checked=true;
  h.form.events.change({target:{name:'enabled'}});
  h.context.api=async () => {throw new Error('disk unavailable');};
  await h.form.events.submit({preventDefault:() => {}});
  h.context.renderInteraction(care());
  h.context.updateCareButtons();
  assert.match(h.element('#interaction-save-status').textContent,/未能保存：disk unavailable/);
  assert.equal(h.form.dataset.saveState,'error');
  assert.equal(h.element('#save-interaction').disabled,false);
  h.context.api=async () => care({enabled:true});
  await h.form.events.submit({preventDefault:() => {}});
  assert.equal(h.form.dataset.saveState,'saved');
  assert.equal(h.element('#save-interaction').disabled,true);
});

test('a late care response updates values without restarting a preview on another page',async () => {
  const h=harness(), fed=deferred();
  h.context.state.interaction=care({enabled:true});
  h.context.renderInteraction(h.context.state.interaction);
  h.context.api=() => fed.promise;
  const feeding=h.feeds[0].events.click();
  h.element('#page-interaction').hidden=true;
  h.documentEvents['nijika:page']({detail:'skins'});
  fed.resolve({action:'feed',care:care({enabled:true,satiety:100,feed_wait:30})});
  await feeding;
  assert.equal(h.context.state.interaction.satiety,100);
  assert.equal(h.fetches.length,0);
  assert.equal(h.element('#preview-pause').disabled,true);
});

test('narrow windows reveal an offscreen stage when an action is chosen',async () => {
  const h=harness();
  h.context.window.innerWidth=360;
  h.context.window.innerHeight=800;
  h.media.matches=true;
  const stage=h.element('.interaction-stage');
  stage.getBoundingClientRect=() => ({top:-900,bottom:-200});
  await h.context.previewAnimation('nod');
  assert.equal(stage.scrolled.block,'start');
  assert.equal(stage.scrolled.behavior,'auto');
  stage.scrolled=null;
  stage.getBoundingClientRect=() => ({top:160,bottom:740});
  await h.context.previewAnimation('nod');
  assert.equal(stage.scrolled,null);
});
