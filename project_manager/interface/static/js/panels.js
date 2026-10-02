/* ============================================================
   Resizable, collapsible side panels
   ============================================================

   For a row of panels with a draggable boundary between each pair of
   visible neighbours. Written for the test dashboard's three panels
   (tree, evidence, prompt builder) but nothing in it knows that: the
   panel list is passed in.

   The existing splitter in main.js is not reused because it only works
   for a sidebar pinned to the viewport's left edge - it treats
   e.clientX as the width directly - and it cannot collapse anything.
   Both are needed here, and a right-hand panel needs the mirrored
   arithmetic anyway.

   The pure parts (clampWidth, fitPanels, resolveHandles, readState,
   writeState) are exported so they can be checked without a DOM. */

const STORAGE_PREFIX = 'pm.panels.';

/* Handles are 4px in CSS and there are at most two of them. Reserving
   them here rather than measuring the DOM keeps the arithmetic
   answerable: the centre panel's width is what is left over, so an
   unaccounted handle width would show up as a gap that never closes. */
const HANDLE_WIDTH = 4;

/* What the middle panel is guaranteed while it is visible and there is
   more than one thing to drag. It is the number that decides whether
   the side panels can both have their maximum: 520 + 720 needs 1240 of
   window plus handles, and a narrower one has to choose. Below the floor
   the centre is squeezed rather than the sides being refused. */
const CENTRE_FLOOR = 360;

/* The handle count is what tells us whether there is a centre left to
   protect, so it is the single input both the fitter and the drag read.
   Two handles means all three panels are up. */
function centreFloor(handles) {
  return handles > 1 ? CENTRE_FLOOR : 0;
}

export function clampWidth(value, panel) {
  if (!Number.isFinite(value)) return panel.default;
  return Math.min(Math.max(Math.round(value), panel.min), panel.max);
}

/* Where two fixed panels have to share a window too narrow for the two of
   them at once, they shrink towards their minimums together. The centre
   panel is not in this function beyond its floor: past that floor it is
   what is left over, and it is allowed to go to zero, because a user who
   has both side panels open on a small window meant it.

   Scaling is proportional to the overshoot rather than a fixed priority,
   so neither side silently loses all its width first. */
export function fitPanels(containerWidth, left, right, handles = 0) {
  const mins = [left.min, right.min];
  const available = containerWidth - handles * HANDLE_WIDTH - centreFloor(handles);

  if (available <= 0) {
    return { left: mins[0], right: mins[1] };
  }

  let wanted = clampWidth(left.width, left) + clampWidth(right.width, right);

  if (wanted <= available) {
    return {
      left: clampWidth(left.width, left),
      right: clampWidth(right.width, right),
    };
  }

  /* Both are above their minimum, so shrink each by the same share of
     the overshoot. */
  let slackLeft = clampWidth(left.width, left) - mins[0];
  let slackRight = clampWidth(right.width, right) - mins[1];
  const totalSlack = slackLeft + slackRight;
  const excess = wanted - available;

  const takeLeft = Math.round((slackLeft / totalSlack) * excess);
  const takeRight = excess - takeLeft;

  return {
    left: clampWidth(clampWidth(left.width, left) - takeLeft, left),
    right: clampWidth(clampWidth(right.width, right) - takeRight, right),
  };
}

/* One handle per gap between two *adjacent visible* panels. So with
   all three up there are two; hide the centre and its two gaps go with
   it, leaving one handle on the only boundary left. Returns the ids of
   the handles to show, in order. */
export function resolveHandles(visible) {
  const shown = [];
  if (visible.left && visible.centre) shown.push('left');
  if (visible.centre && visible.right) shown.push('right');
  /* Centre hidden with both sides up: the left handle now sits on the
     boundary between them. Reusing it keeps one rule - the left handle
     always controls the left edge of whatever is to its right. */
  if (!visible.centre && visible.left && visible.right) shown.push('left');
  return shown;
}

export function readState(key) {
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + key);
    if (!raw) return {};
    const value = JSON.parse(raw);
    return value && typeof value === 'object' ? value : {};
  } catch {
    /* A corrupt or unreadable store is not worth an error page; it just
       means this session starts on the defaults. */
    return {};
  }
}

export function writeState(key, state) {
  try {
    window.localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(state));
  } catch {
    /* Private mode, quota, disabled storage. The panels still work for
       this session; they just will not remember. */
  }
}

/* ============================================================
   LAYOUT
   ============================================================ */

/**
 * Wire a panel row.
 *
 * @param {object} spec
 *   container   - element the panels live in
 *   left/right  - {element, panel:{min,max,default}} fixed-width sides
 *   centre      - {element} the flexible middle
 *   handleLeft/handleRight - the two draggable dividers
 *   storageKey  - localStorage suffix
 *   onLayout    - called after every width or visibility change
 */
export function init(spec) {
  const { container, left, right, centre } = spec;
  const handleLeft = spec.handleLeft;
  const handleRight = spec.handleRight;
  const onLayout = spec.onLayout || (() => {});

  const state = readState(spec.storageKey);

  const widths = {
    left: clampWidth(state.left, left.panel),
    right: clampWidth(state.right, right.panel),
  };

  let hidden = {
    left: state.leftHidden === true,
    centre: state.centreHidden === true,
    right: state.rightHidden === true,
  };

  function visible() {
    return {
      left: !hidden.left,
      centre: !hidden.centre,
      right: !hidden.right,
    };
  }

  /* Apply widths to the two fixed sides. The centre's width is left to
     flexbox: everything not claimed by the sides and handles. */
  function handleCount() {
    return resolveHandles(visible()).length;
  }

  function applyWidths() {
    const room = container.getBoundingClientRect().width;
    const fitted = fitPanels(
      room,
      { width: widths.left, min: left.panel.min, max: left.panel.max },
      { width: widths.right, min: right.panel.min, max: right.panel.max },
      handleCount(),
    );

    widths.left = fitted.left;
    widths.right = fitted.right;

    left.element.style.width = widths.left + 'px';
    right.element.style.width = widths.right + 'px';
  }

  function applyVisibility() {
    const show = visible();

    left.element.hidden = !show.left;
    centre.element.hidden = !show.centre;
    right.element.hidden = !show.right;

    /* With the centre gone the right panel takes the free space instead
       of leaving a dead gap the only remaining handle cannot reach. */
    if (!show.centre && show.right) {
      right.element.style.flex = '1 1 auto';
      right.element.style.minWidth = right.panel.min + 'px';
    } else {
      right.element.style.flex = '0 0 auto';
      right.element.style.minWidth = '';
    }

    const handles = resolveHandles(show);
    handleLeft.hidden = !handles.includes('left');
    handleRight.hidden = !handles.includes('right');

    /* State is published as aria-pressed rather than as a class: the
       toggle button *is* the control, so its pressed state is the
       truthful thing to announce, and the host styles it off that. */
    for (const [id, element] of Object.entries(spec.toggles || {})) {
      element.setAttribute('aria-pressed', String(!hidden[id]));
    }
  }

  function layout() {
    applyVisibility();
    applyWidths();
    onLayout();
  }

  function persist() {
    writeState(spec.storageKey, {
      left: widths.left,
      right: widths.right,
      leftHidden: hidden.left,
      centreHidden: hidden.centre,
      rightHidden: hidden.right,
    });
  }

  /* The handle never follows the cursor past a panel's own bounds, and
     once the centre is down to its floor the handle starts pushing the
     opposite side in rather than stealing from it. Both numbers come
     from the same helpers the fitter uses, so a drag and a layout pass
     cannot disagree about what fits.

     `which` and `other` are slot names, not the spec objects - `right`
     in this scope is {element, panel}, so indexing `widths` with it
     would file the value under "[object Object]" and the opposite
     panel would never actually yield. */
  function dragWidth(which, clientX, rect) {
    const panel = which === 'left' ? left.panel : right.panel;
    const other = which === 'left' ? right.panel : left.panel;
    const room = rect.width;
    const handles = handleCount();
    const floor = centreFloor(handles);

    let width = which === 'left'
      ? clientX - rect.left
      : rect.right - clientX;

    const roomForCentre = room - widths.left - widths.right - handles * HANDLE_WIDTH;

    if (roomForCentre < floor) {
      width += roomForCentre - floor;
    }

    widths[which] = clampWidth(width, panel);

    /* The opposite side gives up only what it can spare, and never drops
       below its own minimum. */
    const spare = room - widths[which] - handles * HANDLE_WIDTH - floor;
    const otherSlot = which === 'left' ? 'right' : 'left';
    widths[otherSlot] = Math.max(Math.min(widths[otherSlot], spare), other.min);
  }

  function beginDrag(which, event) {
    event.preventDefault();

    const move = (moveEvent) => {
      dragWidth(which, moveEvent.clientX, container.getBoundingClientRect());
      applyWidths();
      onLayout();
    };

    const end = () => {
      document.removeEventListener('mousemove', move);
      document.removeEventListener('mouseup', end);
      document.body.classList.remove('panel-dragging');
      applyWidths();
      onLayout();
      persist();
    };

    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', end);
    document.body.classList.add('panel-dragging');
  }

  handleLeft.addEventListener('mousedown', (event) => beginDrag('left', event));
  handleRight.addEventListener('mousedown', (event) => beginDrag('right', event));

  /* Double-click is the reset. Without it the only way back to a
     comfortable width is to drag there by hand. */
  for (const [which, handle] of [['left', handleLeft], ['right', handleRight]]) {
    handle.addEventListener('dblclick', () => {
      widths[which] = spec[which].panel.default;
      applyWidths();
      onLayout();
      persist();
    });

    /* Arrows for keyboard resizing, Home/End for the bounds. The
       splitter is focusable, so it has to be operable without a mouse. */
    handle.addEventListener('keydown', (event) => {
      const step = event.shiftKey ? 40 : 16;
      const panel = spec[which].panel;
      let next = null;

      if (event.key === 'ArrowLeft') {
        next = (which === 'left' ? widths[which] - step : widths[which] + step);
      } else if (event.key === 'ArrowRight') {
        next = (which === 'left' ? widths[which] + step : widths[which] - step);
      } else if (event.key === 'Home') {
        next = panel.min;
      } else if (event.key === 'End') {
        next = panel.max;
      }

      if (next === null) return;
      event.preventDefault();
      widths[which] = clampWidth(next, panel);
      applyWidths();
      onLayout();
      persist();
    });
  }

  for (const [id, element] of Object.entries(spec.toggles || {})) {
    element.addEventListener('click', () => {
      hidden[id] = !hidden[id];
      layout();
      persist();
    });
  }

  layout();

  return {
    layout,
    /* The host needs this to bring back a panel it collapsed itself -
       "Show evidence" un-hides the centre when it is not visible. */
    show(slot) {
      if (!hidden[slot]) return false;
      hidden[slot] = false;
      layout();
      persist();
      return true;
    },
    /* Counterpart to show(): the in-panel chevron collapses a side. The
       reopen control lives outside the panel, so it is not lost with it. */
    hide(slot) {
      if (hidden[slot]) return false;
      hidden[slot] = true;
      layout();
      persist();
      return true;
    },
    toggle(slot) {
      hidden[slot] = !hidden[slot];
      layout();
      persist();
      return !hidden[slot];
    },
    isVisible: (slot) => !hidden[slot],
  };
}

export default { init, clampWidth, fitPanels, resolveHandles, readState, writeState };