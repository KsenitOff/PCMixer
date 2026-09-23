const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../app/static/app.js'), 'utf8');
const setup = source.slice(0, source.indexOf('function makeChannel'));
const refresh = source.slice(source.indexOf('async function refresh()'), source.indexOf('async function requestWakeLock()'));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function load(fetch) {
  const connection = {classList: {add() {}, remove() {}}};
  const context = {
    document: {querySelector: () => connection},
    fetch,
    setTimeout,
    clearTimeout,
    Date,
    console,
  };
  vm.runInNewContext(`${setup}\n${refresh}\nglobalThis.api = {state, scheduleVolume, refresh};`, context);
  return context.api;
}

test('continuous movement sends updates before release and ends at the latest value', async () => {
  const sent = [];
  const api = load(async (url, options) => {
    if (url === '/api/volume') {
      sent.push(JSON.parse(options.body).volume);
      await sleep(12);
    }
    return {ok: true, json: async () => ({poll_ms: 450})};
  });
  api.state.dragging = {pointerId: 1};
  for (let value = 10; value <= 90; value += 10) {
    api.scheduleVolume('chrome.exe', value);
    await sleep(12);
  }
  assert.ok(sent.length > 1, `Only ${sent.length} update(s) during the drag`);
  api.scheduleVolume('chrome.exe', 93, true);
  await sleep(80);
  assert.equal(sent.at(-1), 93);
  assert.ok(sent.length < 11, 'Intermediate updates should be coalesced');
});

test('state polling continues while a fader is being dragged', async () => {
  let polls = 0;
  const api = load(async (url) => {
    assert.equal(url, '/api/state');
    polls += 1;
    return {ok: true, json: async () => ({poll_ms: 250})};
  });
  api.state.dragging = {pointerId: 1};
  await api.refresh();
  assert.ok(api.state.pollTimer, 'Next poll must be scheduled');
  await sleep(280);
  assert.ok(polls >= 2, `Only ${polls} state poll(s)`);
  clearTimeout(api.state.pollTimer);
});

test('every channel for the same app moves together during a drag', () => {
  const channels = ['chrome.exe', 'chrome.exe', 'discord.exe'].map((key) => {
    const fill = {style: {}};
    const thumb = {style: {}};
    const readout = {textContent: ''};
    const channel = {
      dataset: {key},
      querySelector: (selector) => selector === '.fader' ? fader : readout,
    };
    const fader = {
      querySelector: (selector) => selector === '.fader-fill' ? fill : thumb,
      closest: () => channel,
      setAttribute(name, value) { this[name] = value; },
    };
    return {channel, fader, fill, thumb, readout};
  });
  const context = {document: {querySelectorAll: () => channels.map((x) => x.channel)}};
  const visuals = source.slice(source.indexOf('function setFaderVisual('), source.indexOf('function volumeFromPointer('));
  vm.runInNewContext(`${visuals}\nglobalThis.update = setTargetFaderVisual;`, context);
  context.update('chrome.exe', 64);
  assert.deepEqual(channels.map((x) => x.readout.textContent), ['64%', '64%', '']);
  assert.deepEqual(channels.map((x) => x.fill.style.height), ['64%', '64%', undefined]);
});

test('settings list shows current audio apps and keeps an offline assignment', () => {
  const elements = new Map();
  for (let i = 0; i < 4; i += 1) {
    const select = {
      options: [],
      _value: '',
      replaceChildren(...options) { this.options = options; this._value = ''; },
      set value(value) { this._value = this.options.some((option) => option.value === value) ? value : ''; },
      get value() { return this._value; },
    };
    const custom = {value: '', classList: {toggle() {}}};
    elements.set(`#fixed-${i}`, select);
    elements.set(`#fixed-custom-${i}`, custom);
  }
  const context = {
    state: {settingsOptionsKey: ''},
    document: {querySelector: (selector) => elements.get(selector), createElement: () => ({})},
  };
  const settings = source.slice(source.indexOf('const CUSTOM_APP'), source.indexOf('async function refresh()'));
  vm.runInNewContext(`const $ = (selector) => document.querySelector(selector);\n${settings}\nglobalThis.populate = populateAppSelects;`, context);
  context.populate({
    active: [
      {key: 'chrome.exe', exe: 'chrome.exe', name: 'Chrome'},
      {key: 'discord.exe', exe: 'Discord.exe', name: 'Discord'},
    ],
    fixed_config: ['CHROME.EXE', 'firefox.exe', '', ''],
  }, false);
  const first = elements.get('#fixed-0');
  const second = elements.get('#fixed-1');
  assert.equal(first.value, 'chrome.exe');
  assert.ok(first.options.some((option) => option.textContent === 'Discord · Discord.exe'));
  assert.equal(second.value, 'firefox.exe');
  assert.ok(second.options.some((option) => option.textContent === 'firefox.exe (offline)'));
  assert.ok(second.options.some((option) => option.textContent === 'Enter .exe manually…'));
});
