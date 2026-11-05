'use strict';
const byId = id => document.getElementById(id);
const source = byId('source'), preview = byId('preview');
const videos = [source, preview];
let manifest, playing = false, loops = 0, lastMediaTime = 0, generation = 0;
const ready = video => new Promise((resolve, reject) => {
  if (video.readyState >= 2) return resolve();
  video.addEventListener('loadeddata', resolve, {once:true});
  video.addEventListener('error', () => reject(new Error('视频加载失败，请检查本机导出。')), {once:true});
});
function display() {
  const time = preview.currentTime;
  byId('position').value = time;
  byId('clock').textContent = `${time.toFixed(2)} / ${manifest.duration_seconds.toFixed(2)} 秒`;
  const quality = preview.getVideoPlaybackQuality?.();
  byId('metrics').textContent = `${manifest.size.join(' × ')} · ${manifest.fps} fps · ${manifest.frames} 帧 · 已循环 ${loops} 次 · 浏览器丢帧 ${quality?.droppedVideoFrames ?? '未提供'} / ${quality?.totalVideoFrames ?? '未提供'}`;
}
function pause(message = '已暂停；可逐帧检查。') {
  generation++;
  playing = false;
  videos.forEach(video => video.pause());
  byId('play').textContent = '一起播放';
  byId('status').textContent = message;
}
function seek(time) {
  pause();
  // Sample inside a frame, avoiding boundary rounding to the preceding frame.
  const target = Math.min((manifest.frames - 0.5) / manifest.fps, Math.max(0, time));
  videos.forEach(video => {video.currentTime = target;});
  lastMediaTime = target;
  display();
}
async function play() {
  const sequence = ++generation;
  source.currentTime = preview.currentTime;
  playing = true;
  byId('play').textContent = '正在准备…';
  try {
    await Promise.all(videos.map(video => video.play()));
    if (sequence !== generation || document.hidden) {
      if (sequence === generation) pause('页面离开，已暂停。');
      return;
    }
    playing = true;
    byId('play').textContent = '暂停';
    byId('status').textContent = '正在同步播放；往返会出现反向运动，请留意自然程度。';
  } catch (_) {
    if (sequence === generation) pause('浏览器未开始播放，请再点一次“一起播放”。');
  }
}
function onFrame() {
  if (manifest) {
    if (playing && preview.currentTime < lastMediaTime - 0.5) loops++;
    lastMediaTime = preview.currentTime;
    if (playing && !source.seeking && !preview.seeking && Math.abs(source.currentTime - preview.currentTime) > 0.12) {
      source.currentTime = preview.currentTime;
    }
    display();
  }
  if (preview.requestVideoFrameCallback) preview.requestVideoFrameCallback(onFrame);
}
byId('play').onclick = () => playing ? pause() : play();
byId('restart').onclick = () => {seek(0); lastMediaTime = 0; play();};
byId('position').oninput = event => seek(Number(event.target.value));
byId('previous').onclick = () => seek((Math.floor(preview.currentTime * manifest.fps + 0.001) - 0.5) / manifest.fps);
byId('next').onclick = () => seek((Math.floor(preview.currentTime * manifest.fps + 0.001) + 1.5) / manifest.fps);
byId('speed').onchange = event => {videos.forEach(video => {video.playbackRate = Number(event.target.value);});};
byId('backdrop').onchange = event => {byId('background').className = `stage ${event.target.value}`;};
byId('turn').onclick = () => {seek(Math.max(0, manifest.duration_seconds / 2 - 0.5)); play();};
byId('seam').onclick = () => {seek(manifest.duration_seconds - 0.7); play();};
document.addEventListener('visibilitychange', () => {if (document.hidden) pause('页面离开，已暂停。');});
videos.forEach(video => video.addEventListener('error', () => pause('视频加载失败，请检查本机导出。')));
preview.addEventListener('seeked', () => {if (manifest) display();});
async function init() {
  try {
    const response = await fetch('/review.json');
    if (!response.ok) throw new Error('读取样片信息失败。');
    manifest = await response.json();
    await Promise.all(videos.map(ready));
    videos.forEach(video => {video.loop = true;});
    byId('position').max = manifest.duration_seconds;
    document.querySelectorAll('button,input').forEach(control => {control.disabled = false;});
    byId('turn').hidden = manifest.loop_mode !== 'ping-pong';
    byId('status').textContent = '样片已就绪。点击“一起播放”，或用方向键调整进度。';
    if (preview.requestVideoFrameCallback) preview.requestVideoFrameCallback(onFrame);
    else preview.addEventListener('timeupdate', display);
    display();
  } catch (error) {
    byId('status').textContent = error.message;
  }
}
init();
