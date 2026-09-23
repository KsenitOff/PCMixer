const state = {
  data: null,
  tab: 'fixed',
  dragging: null,
  connected: false,
  pollTimer: null,
  polling: false,
  refreshAgain: false,
  wakeLock: null,
  volumeRequests: new Map(),
  muteRequests: 0,
  settingsOptionsKey: '',
  settingsInitialized: false,
};

const $ = (sel) => document.querySelector(sel);
const fixedGrid = $('#fixed-grid');
const activeGrid = $('#active-grid');
const activeEmpty = $('#active-empty');
const connection = $('#connection');

function prettyRole(role) {
  if (role === 'FOCUS') return 'FOCUS';
  if (role === 'FIXED') return 'FIXED';
  return '';
}

function setTab(tab) {
  state.tab = tab;
  $('#tab-fixed').classList.toggle('active', tab === 'fixed');
  $('#tab-active').classList.toggle('active', tab === 'active');
  $('#fixed-panel').classList.toggle('active', tab === 'fixed');
  $('#active-panel').classList.toggle('active', tab === 'active');
}

function setFaderVisual(el, value) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  el.querySelector('.fader-fill').style.height = `${v}%`;
  el.querySelector('.fader-thumb').style.bottom = `${v}%`;
  el.setAttribute('aria-valuenow', String(v));
  el.closest('.channel').querySelector('.volume-readout').textContent = `${Math.round(v)}%`;
}

function setTargetFaderVisual(target, value) {
  document.querySelectorAll('.channel').forEach((channel) => {
    if (channel.dataset.key === target) {
      setFaderVisual(channel.querySelector('.fader'), value);
    }
  });
}

function volumeFromPointer(fader, event) {
  const rect = fader.getBoundingClientRect();
  const y = Math.max(rect.top, Math.min(rect.bottom, event.clientY));
  return Math.round((1 - (y - rect.top) / rect.height) * 100);
}

function hasPendingVolume() {
  return [...state.volumeRequests.values()].some((request) =>
    request.inFlight || request.timer || request.latest !== null);
}

function scheduleVolume(target, volume, immediate = false) {
  if (!target) return;
  let request = state.volumeRequests.get(target);
  if (!request) {
    request = {latest: null, inFlight: false, timer: null, lastSent: 0};
    state.volumeRequests.set(target, request);
  }
  request.latest = volume;
  if (request.inFlight) return;
  if (request.timer) clearTimeout(request.timer);
  const delay = immediate ? 0 : Math.max(0, 35 - (Date.now() - request.lastSent));
  request.timer = setTimeout(async () => {
    request.timer = null;
    if (request.inFlight || request.latest === null) return;
    const next = request.latest;
    request.latest = null;
    request.inFlight = true;
    request.lastSent = Date.now();
    try {
      const response = await fetch('/api/volume', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({target, volume: next}),
      });
      if (!response.ok) throw new Error('volume failed');
    } catch (_) {
      if (!state.dragging) refresh();
    } finally {
      request.inFlight = false;
      if (request.latest !== null) scheduleVolume(target, request.latest, true);
      else if (!state.dragging) refresh();
    }
  }, delay);
}

function makeChannel(item) {
  const tpl = $('#channel-template').content.cloneNode(true);
  const root = tpl.querySelector('.channel');
  const fader = tpl.querySelector('.fader');
  const muteBtn = tpl.querySelector('.mute-btn');

  root.dataset.key = item.key || '';
  root.classList.toggle('unavailable', !item.available);
  root.classList.toggle('muted', !!item.muted);
  tpl.querySelector('.channel-role').textContent = prettyRole(item.role);
  tpl.querySelector('.channel-name').textContent = item.name || 'Unknown';
  tpl.querySelector('.channel-exe').textContent = item.exe || '';
  muteBtn.textContent = item.muted ? '🔇' : '🔊';
  muteBtn.classList.toggle('muted', !!item.muted);
  setFaderVisual(fader, item.volume);

  if (item.available && item.key) {
    fader.addEventListener('pointerdown', (e) => {
      if (state.dragging) return;
      state.dragging = {fader, pointerId: e.pointerId, target: item.key};
      fader.setPointerCapture(e.pointerId);
      const v = volumeFromPointer(fader, e);
      setTargetFaderVisual(item.key, v);
      scheduleVolume(item.key, v, true);
      e.preventDefault();
    });
    fader.addEventListener('pointermove', (e) => {
      if (state.dragging?.fader !== fader || state.dragging.pointerId !== e.pointerId) return;
      const v = volumeFromPointer(fader, e);
      setTargetFaderVisual(item.key, v);
      scheduleVolume(item.key, v, false);
      e.preventDefault();
    });
    const finish = (e) => {
      if (state.dragging?.fader !== fader || state.dragging.pointerId !== e.pointerId) return;
      const v = volumeFromPointer(fader, e);
      setTargetFaderVisual(item.key, v);
      scheduleVolume(item.key, v, true);
      state.dragging = null;
    };
    fader.addEventListener('pointerup', finish);
    fader.addEventListener('pointercancel', finish);
    fader.addEventListener('lostpointercapture', (e) => {
      if (state.dragging?.fader === fader && state.dragging.pointerId === e.pointerId) {
        state.dragging = null;
        scheduleVolume(item.key, Number(fader.getAttribute('aria-valuenow')), true);
      }
    });
    fader.addEventListener('keydown', (e) => {
      const current = Number(fader.getAttribute('aria-valuenow') || 0);
      let next = current;
      if (e.key === 'ArrowUp' || e.key === 'ArrowRight') next = Math.min(100, current + 2);
      if (e.key === 'ArrowDown' || e.key === 'ArrowLeft') next = Math.max(0, current - 2);
      if (next !== current) {
        setTargetFaderVisual(item.key, next);
        scheduleVolume(item.key, next, true);
        e.preventDefault();
      }
    });

    muteBtn.addEventListener('click', async () => {
      const muted = !root.classList.contains('muted');
      document.querySelectorAll('.channel').forEach((channel) => {
        if (channel.dataset.key !== item.key) return;
        channel.classList.toggle('muted', muted);
        const button = channel.querySelector('.mute-btn');
        button.classList.toggle('muted', muted);
        button.textContent = muted ? '🔇' : '🔊';
      });
      state.muteRequests += 1;
      try {
        const response = await fetch('/api/mute', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({target: item.key, muted}),
        });
        if (!response.ok) throw new Error('mute failed');
      } catch (_) {
        // The next state poll restores the real value after a failed write.
      } finally {
        state.muteRequests -= 1;
        refresh();
      }
    });
  } else {
    fader.setAttribute('aria-disabled', 'true');
    muteBtn.disabled = true;
  }
  return tpl;
}

function render(data) {
  state.data = data;
  fixedGrid.replaceChildren(...data.fixed.map(makeChannel));
  activeGrid.replaceChildren(...data.active.map(makeChannel));
  activeEmpty.classList.toggle('hidden', data.active.length > 0);

  const settingsOpen = !$('#settings-modal').classList.contains('hidden');
  if (settingsOpen) {
    const optionsKey = JSON.stringify(data.active.map(({key, exe, name}) => [key, exe, name]));
    if (!state.settingsInitialized) {
      populateAppSelects(data, false);
      $('#autostart').checked = !!data.autostart;
      state.settingsInitialized = true;
    } else if (optionsKey !== state.settingsOptionsKey) {
      populateAppSelects(data, true);
    }
  }

  const urlBox = $('#lan-urls');
  urlBox.replaceChildren(...(data.lan_urls.length ? data.lan_urls : ['No private LAN address detected']).map((url) => {
    if (url.startsWith('http')) {
      const a = document.createElement('a');
      a.href = url;
      a.textContent = url;
      return a;
    }
    const span = document.createElement('span');
    span.textContent = url;
    return span;
  }));
}

const CUSTOM_APP = '__custom_app__';

function showCustomInput(index) {
  const select = $(`#fixed-${index}`);
  const custom = $(`#fixed-custom-${index}`);
  custom.classList.toggle('hidden', select.value !== CUSTOM_APP);
}

function populateAppSelects(data, preserve) {
  state.settingsOptionsKey = JSON.stringify(data.active.map(({key, exe, name}) => [key, exe, name]));
  for (let i = 0; i < 4; i += 1) {
    const select = $(`#fixed-${i}`);
    const custom = $(`#fixed-custom-${i}`);
    const editingCustom = preserve && select.value === CUSTOM_APP;
    const chosen = preserve
      ? (editingCustom ? custom.value.trim() : select.value)
      : (data.fixed_config[i] || '');
    const activeChoice = data.active.find((app) => app.exe.toLowerCase() === chosen.toLowerCase());
    const options = [];
    const add = (value, label) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      options.push(option);
    };
    add('', 'Not assigned');
    for (const app of data.active) {
      add(app.exe, `${app.name} · ${app.exe}`);
    }
    if (chosen && !activeChoice) {
      add(chosen, `${chosen} (offline)`);
    }
    add(CUSTOM_APP, 'Enter .exe manually…');
    select.replaceChildren(...options);
    select.value = editingCustom ? CUSTOM_APP : (activeChoice?.exe || chosen);
    if (!preserve) custom.value = chosen;
    showCustomInput(i);
  }
}

async function refresh() {
  if (state.polling) {
    state.refreshAgain = true;
    return;
  }
  clearTimeout(state.pollTimer);
  state.pollTimer = null;
  state.polling = true;
  let delay = 1100;
  try {
    const res = await fetch('/api/state', {cache: 'no-store'});
    if (!res.ok) throw new Error('state failed');
    const data = await res.json();
    state.connected = true;
    connection.classList.add('online');
    if (!state.dragging && !hasPendingVolume() && !state.muteRequests) render(data);
    delay = Math.max(250, Number(data.poll_ms) || 450);
  } catch (_) {
    state.connected = false;
    connection.classList.remove('online');
  } finally {
    state.polling = false;
    state.pollTimer = setTimeout(refresh, state.refreshAgain ? 0 : delay);
    state.refreshAgain = false;
  }
}

async function requestWakeLock() {
  if (!('wakeLock' in navigator)) return;
  try { state.wakeLock = await navigator.wakeLock.request('screen'); } catch (_) {}
}

$('#tab-fixed').addEventListener('click', () => setTab('fixed'));
$('#tab-active').addEventListener('click', () => setTab('active'));

$('#settings-btn').addEventListener('click', () => {
  state.settingsInitialized = false;
  $('#settings-error').classList.add('hidden');
  if (state.data) {
    populateAppSelects(state.data, false);
    $('#autostart').checked = !!state.data.autostart;
    state.settingsInitialized = true;
  }
  $('#settings-modal').classList.remove('hidden');
  $('#settings-modal').setAttribute('aria-hidden', 'false');
  refresh();
});
for (let i = 0; i < 4; i += 1) {
  $(`#fixed-${i}`).addEventListener('change', () => {
    showCustomInput(i);
    if ($(`#fixed-${i}`).value === CUSTOM_APP) $(`#fixed-custom-${i}`).focus();
  });
}
$('#close-settings').addEventListener('click', () => {
  $('#settings-modal').classList.add('hidden');
  $('#settings-modal').setAttribute('aria-hidden', 'true');
});
$('#settings-modal').addEventListener('click', (e) => {
  if (e.target.id === 'settings-modal') $('#close-settings').click();
});
$('#save-settings').addEventListener('click', async () => {
  const fixed_apps = [0,1,2,3].map((i) => {
    const selected = $(`#fixed-${i}`).value;
    return (selected === CUSTOM_APP ? $(`#fixed-custom-${i}`).value : selected).trim();
  });
  const btn = $('#save-settings');
  const error = $('#settings-error');
  btn.disabled = true;
  error.classList.add('hidden');
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({fixed_apps, autostart: $('#autostart').checked}),
    });
    if (!res.ok) throw new Error('save failed');
    $('#close-settings').click();
    await refresh();
  } catch (_) {
    error.textContent = 'Could not save settings. Check the PC connection and try again.';
    error.classList.remove('hidden');
  } finally {
    btn.disabled = false;
  }
});

$('#fullscreen-btn').addEventListener('click', async () => {
  try {
    if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
    else await document.exitFullscreen();
  } catch (_) {}
  requestWakeLock();
});

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    requestWakeLock();
    refresh();
  }
});

requestWakeLock();
refresh();
