/* ============================================================
   Header test report formatting
   ============================================================

   The text a saved report is written in, and the filename it gets.
   No DOM and no fetch, so both can be checked without a browser.

   Separate from the dashboard that shows the report because this is
   formatting with real branching - missing summary, missing prompt,
   agent ids that are not filenames - and inline in test.html it could
   only be checked by running a model.

   buildReportText() is the one definition of what a report reads like.
   The on-screen renderer in test.html and this file can disagree about
   wording, but they cannot disagree about content: both read the same
   object. */

/* The four headers in suite order. Anything the report carries that is
   not one of these is appended, so a suite that grows a fifth header
   produces a file that mentions it rather than dropping it. */
const HEADERS = ['role', 'user', 'purpose', 'hallucinations'];

/* Indent two spaces so a reply that contains its own blank lines or
   something dash-shaped cannot be read as the next section heading.
   Nothing an agent can say survives the two-space indent as a
   top-level marker. */
const INDENT = '  ';

const UNDERLINE = '='.repeat(60);
const RULE = '-'.repeat(5);

function field(value, fallback = '?') {
  const text = value === undefined || value === null ? '' : String(value).trim();
  return text || fallback;
}

function block(text, fallback = '(empty)') {
  const body = (text === undefined || text === null ? '' : String(text)).trim();
  /* The fallback is indented too. An unindented "(empty)" would be the
     only body line in the file that sits at column zero, and a reader
     scanning for headings would take it for one. */
  if (!body) return INDENT + fallback;
  return body
    .split('\n')
    .map((line) => INDENT + line)
    .join('\n');
}

/* "2026-09-30 14:22:31" for an ISO string, or the raw value when the
   report carries something unparseable. A wrong-but-present timestamp
   is better than a blank field, because the point of the line is to
   tell two saved reports apart. */
function readableTime(value) {
  if (!value) return '?';
  const when = new Date(value);
  if (isNaN(when)) return String(value);
  return when.toLocaleString();
}

/**
 * Render a report as the text of a saved file.
 *
 * @param {object} report - {summary, results} as GET /api/test/results
 *                          returns it. Any field may be missing.
 * @returns {string} the report, newline-terminated.
 */
export function buildReportText(report) {
  const data = report || {};
  const summary = data.summary || {};
  const results = Array.isArray(data.results) ? data.results : [];

  /* An absent total is filled from the rows, but only if there are any:
     a report with neither a summary nor rows has no total to report, and
     "0 of 0" would read as a real run of nothing. */
  const total = summary.total === undefined
    ? (results.length ? results.length : '?')
    : summary.total;
  const passed = summary.passed === undefined ? '?' : summary.passed;
  const failed = summary.failed === undefined ? '?' : summary.failed;

  /* FAIL only when something is positively known to have failed. An
     absent summary.failed falls back to the rows; with neither, the
     verdict is '?' rather than a pass nobody can support. */
  const known = summary.total !== undefined
    || summary.failed !== undefined
    || results.length > 0;
  const anyFailed = summary.failed === undefined
    ? results.some((row) => row && row.status && row.status !== 'PASS')
    : summary.failed > 0;
  const verdict = !known ? '?' : (anyFailed ? 'FAIL' : 'PASS');

  const lines = [];

  lines.push('Agent Header Test Report');
  lines.push(UNDERLINE);
  lines.push('Agent    : ' + field(summary.agent_id, '(unknown)'));
  lines.push('Model    : ' + field(summary.model, "(the agent's own model)"));
  lines.push('Ran at   : ' + readableTime(summary.ran_at));
  lines.push(
    'Result   : ' + verdict
    + ' - ' + passed + ' of ' + total + ' passed'
    + (summary.failed ? ', ' + failed + ' failed' : '')
  );
  if (summary.results_file) {
    lines.push('Evidence : ' + summary.results_file);
  }

  if (!results.length) {
    lines.push('');
    lines.push('No results were recorded in this report.');
    return lines.join('\n') + '\n';
  }

  /* Suite order first so the file reads the same way every time, then
     anything unrecognised. The dashboard renders the same way. */
  const ordered = [];
  for (const name of HEADERS) {
    for (const row of results) {
      if (row && row.section === name) ordered.push(row);
    }
  }
  for (const row of results) {
    if (row && !HEADERS.includes(row.section)) ordered.push(row);
  }

  for (const row of ordered) {
    lines.push('');
    lines.push(String(row.section || 'unknown').toUpperCase());
    lines.push(RULE);
    lines.push('Status : ' + field(row.status, '?'));
    if (row.reason) lines.push('Reason : ' + String(row.reason).trim());
    lines.push('Prompt :');
    lines.push(block(row.prompt));
    lines.push('Reply  :');
    lines.push(block(row.response));
  }

  return lines.join('\n') + '\n';
}

/* Same sanitiser the chat export uses (routers/chat.py): anything that
   is not a letter, digit, underscore or dash collapses to a dash. It
   also strips the characters Windows forbids in a filename, which is
   the whole reason the agent id is not trusted verbatim. */
function safeSegment(value, fallback, maxLength) {
  const cleaned = String(value === undefined || value === null ? '' : value)
    .replace(/[^A-Za-z0-9_-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, maxLength);
  return cleaned || fallback;
}

/* YYYYMMDD-HHMMSS, local time. No colons: Windows rejects them in a
   filename, and a save that silently fails on the user's own machine is
   worse than a slightly ugly name. */
function timestamp(date) {
  const when = date instanceof Date && !isNaN(date) ? date : new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return [
    when.getFullYear(),
    pad(when.getMonth() + 1),
    pad(when.getDate()),
    '-',
    pad(when.getHours()),
    pad(when.getMinutes()),
    pad(when.getSeconds()),
  ].join('');
}

/**
 * The filename a saved report gets.
 *
 * Timestamp-per-run, so successive saves accumulate instead of
 * overwriting, and each one is distinguishable by name.
 *
 * @param {object} summary - the report's summary object.
 * @param {Date}   [when]   - injectable so the name is testable.
 * @returns {string} e.g. 'test_report_demo_agent_20260930-142231.txt'
 */
export function reportFileName(summary, when) {
  const agent = safeSegment((summary || {}).agent_id, 'unknown-agent', 40);
  return 'test_report_' + agent + '_' + timestamp(when) + '.txt';
}

export default { buildReportText, reportFileName };