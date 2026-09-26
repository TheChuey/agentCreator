/* Stable per-agent color module

   An agent must show the same color everywhere it appears (home
   card, chat header chip), with nothing persisted between pages.
   Colors are therefore derived from the agent id itself via a
   stable hash, so both pages agree without coordinating.

   The palette is hand-picked to stay legible on both dark themes
   in use: the home page (#1e1e1e) and chat (#131822). */

const AGENT_PALETTE = [
  '#4fc3f7', // sky
  '#81c784', // green
  '#ffb74d', // amber
  '#ba68c8', // violet
  '#f06292', // rose
  '#4dd0e1', // cyan
  '#aed581', // lime
  '#ff8a65', // coral
  '#9575cd', // indigo
  '#ffd54f', // yellow
  '#4db6ac', // teal
  '#e57373'  // red
];

/* FNV-1a: cheap, stable across page loads, and well spread for
   short ids like "rag_assistant". */
function hashId(id) {
  let hash = 0x811c9dc5;
  const text = String(id == null ? '' : id);
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

function agentColor(id) {
  return AGENT_PALETTE[hashId(id) % AGENT_PALETTE.length];
}

/* Hash collisions give two agents the same color. Nudging later
   agents to the next free slot keeps every visible card distinct.
   The result stays deterministic for a given list order, so the
   home page and the chat page always agree.

   Once every slot is taken the search gives up and reuses the
   hashed color, so a list longer than the palette degrades to
   shared colors instead of spinning forever. */
function assignAgentColors(agents) {
  const list = Array.isArray(agents) ? agents : [];
  const taken = new Set();
  const colors = new Map();
  for (const agent of list) {
    const id = agent && agent.id;
    if (id == null || colors.has(id)) continue;
    const start = hashId(id) % AGENT_PALETTE.length;
    let slot = start;
    for (let step = 0; step < AGENT_PALETTE.length; step += 1) {
      if (!taken.has(slot)) break;
      slot = (slot + 1) % AGENT_PALETTE.length;
    }
    taken.add(slot);
    colors.set(id, AGENT_PALETTE[slot]);
  }
  return colors;
}

export { AGENT_PALETTE, agentColor, assignAgentColors };
