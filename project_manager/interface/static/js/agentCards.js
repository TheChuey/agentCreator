/* Agent cards module

   Renders one card per available agent on the home page. Each card
   carries the agent's stable color (see agentColors.js) so the same
   agent is recognizable in the chat header. */

import API from './api.js';
import { assignAgentColors } from './agentColors.js';

function openChatWithAgent(agentId) {
  const width = 1100;
  const height = 740;
  const left = Math.max(0, (window.screen.width - width) / 2);
  const top = Math.max(0, (window.screen.height - height) / 2);
  const target = agentId
    ? `/chat?agent=${encodeURIComponent(agentId)}`
    : '/chat';
  window.open(
    target,
    'ProjectManagerChat',
    `width=${width},height=${height},top=${top},left=${left},` +
    'resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no'
  );
}

function buildCard(agent, color) {
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'agent-card';
  card.dataset.agent = agent.id;
  card.style.setProperty('--agent-color', color);
  card.title = 'Chat with ' + agent.name;

  const head = document.createElement('div');
  head.className = 'agent-card-head';

  const swatch = document.createElement('span');
  swatch.className = 'agent-swatch';

  const name = document.createElement('span');
  name.className = 'agent-card-name';
  name.textContent = agent.name;

  head.append(swatch, name);

  const badges = document.createElement('div');
  badges.className = 'agent-card-badges';

  const sourceBadge = document.createElement('span');
  sourceBadge.className = 'agent-badge source';
  sourceBadge.textContent = agent.source === 'workspace' ? 'workspace' : 'library';
  badges.appendChild(sourceBadge);

  if (agent.mode) {
    const modeBadge = document.createElement('span');
    modeBadge.className = 'agent-badge mode';
    modeBadge.textContent = agent.mode;
    badges.appendChild(modeBadge);
  }

  const description = document.createElement('p');
  description.className = 'agent-card-desc';
  description.textContent = agent.description || 'No description provided.';

  card.append(head, badges, description);
  return card;
}

function initAgentCards(options = {}) {
  const host = options.host || document.getElementById('agentCards');
  if (!host) return Promise.resolve([]);

  const onOpen = options.onOpen || openChatWithAgent;

  return API.agents().then((data) => {
    const agents = data.agents || [];
    host.innerHTML = '';

    if (!agents.length) {
      const empty = document.createElement('p');
      empty.className = 'agent-cards-empty';
      empty.textContent = 'No agents found. Create one from the editor to get started.';
      host.appendChild(empty);
      return agents;
    }

    const colors = assignAgentColors(agents);
    for (const agent of agents) {
      const card = buildCard(agent, colors.get(agent.id));
      card.addEventListener('click', () => onOpen(agent.id));
      host.appendChild(card);
    }
    return agents;
  });
}

export { initAgentCards, openChatWithAgent };
