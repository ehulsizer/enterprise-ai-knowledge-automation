const $ = id => document.getElementById(id);
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {'X-API-Key': $('key').value, ...options.headers}});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
function node(tag, text, parent) { const el = document.createElement(tag); el.textContent = text; parent.append(el); return el; }
$('connect').onclick = async () => {
  try { const s = await api('/api/status'); $('status').textContent = `${s.chunks} indexed chunks · ${s.embedding_mode} retrieval · ${s.generation_mode} generation`; }
  catch(e) { $('status').textContent = e.message; }
};
document.querySelectorAll('[data-q]').forEach(b => b.onclick = () => { $('question').value = b.dataset.q; $('question').focus(); });
$('query').onsubmit = async e => {
  e.preventDefault(); $('ask').disabled = true; $('result').replaceChildren(); node('p', 'Retrieving evidence and running the workflow…', $('result'));
  try {
    const r = await api('/api/query', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question: $('question').value, top_k: Number($('topk').value)})});
    $('result').replaceChildren(); node('span', `${r.route.toUpperCase()} · ${r.generation_mode} · ${r.embedding_mode}`, $('result')).className = 'badge';
    node('h2', 'Answer', $('result')); node('pre', r.answer, $('result')).className = 'answer';
    r.warnings.forEach(w => node('p', w, $('result')).className = 'warning');
    if(r.citations.length) node('h3', 'Source evidence', $('result'));
    r.citations.forEach(c => { const d = node('details', '', $('result')); node('summary', `[${c.id}] ${c.source} · page ${c.page} · chunk ${c.chunk} · score ${c.score.toFixed(3)}`, d); node('p', c.text, d); });
    const trace = node('details', '', $('result')); node('summary', 'Workflow trace & operational records', trace); node('pre', JSON.stringify({trace: r.trace, tools: r.tools, operational_data: r.operational_data}, null, 2), trace);
  } catch(e) { $('result').replaceChildren(); node('p', e.message, $('result')).className = 'warning'; }
  finally { $('ask').disabled = false; }
};
$('upload').onclick = async () => {
  if (!$('file').files.length) { $('upload-status').textContent = 'Select a document first.'; return; }
  $('upload').disabled = true;
  try { const f = new FormData(); f.append('file', $('file').files[0]); const r = await api('/api/ingest', {method: 'POST', body: f}); $('upload-status').textContent = `Indexed ${r.chunks} chunks from ${r.source}`; }
  catch(e) { $('upload-status').textContent = e.message; }
  finally { $('upload').disabled = false; }
};
