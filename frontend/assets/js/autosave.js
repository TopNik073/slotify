/** Debounce changes and serialize writes so a slow response cannot overwrite newer edits. */
export function createAutosave({ initial, read, save, onSaved, onState, delay = 600 }) {
  let saved = { ...initial };
  let timer = null;
  let inFlight = null;
  let dueAt = 0;
  let failed = false;

  const changes = () => Object.fromEntries(Object.entries(read()).filter(([key, value]) => value !== saved[key]));
  const dirty = () => Object.keys(changes()).length > 0;
  function clearTimer() {
    clearTimeout(timer);
    timer = null;
  }
  function enqueue() {
    clearTimer();
    timer = setTimeout(() => { timer = null; void persist(); }, Math.max(0, dueAt - Date.now()));
  }
  function schedule() {
    failed = false;
    dueAt = Date.now() + delay;
    clearTimer();
    if (!dirty() && !inFlight) { onState('saved'); return; }
    onState(inFlight ? 'saving' : 'pending');
    enqueue();
  }
  function persist() {
    if (inFlight) return inFlight;
    const patch = changes();
    if (!Object.keys(patch).length) { failed = false; onState('saved'); return Promise.resolve(true); }
    failed = false;
    onState('saving');
    inFlight = Promise.resolve()
      .then(() => save(patch))
      .then((updated) => {
        saved = { ...saved, ...patch };
        onSaved(updated);
        return true;
      })
      .catch((error) => { failed = true; onState('error', error); return false; })
      .finally(() => {
        inFlight = null;
        if (failed) { clearTimer(); return; }
        if (dirty()) { onState('pending'); enqueue(); }
        else { clearTimer(); onState('saved'); }
      });
    return inFlight;
  }
  async function flush() {
    clearTimer();
    if (inFlight && !(await inFlight)) return false;
    clearTimer();
    while (dirty()) {
      if (!(await persist())) return false;
      clearTimer();
    }
    failed = false;
    onState('saved');
    return true;
  }
  return { schedule, flush, get isDirty() { return dirty() || Boolean(inFlight); } };
}
