const result = document.querySelector('#result');
document.querySelector('#protocol').textContent = location.protocol === 'https:' ? 'HTTPS / TLS' : 'HTTP';
async function request(path) {
  const response = await fetch(path, {cache: 'no-store'});
  let body;
  try { body = await response.json(); } catch { throw new Error(`Resposta HTTP ${response.status}. Verifique ALB/WAF.`); }
  if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
  if (body.server) document.querySelector('#server').textContent = body.server;
  return body;
}
async function inspect(path) {
  result.textContent = 'Consultando…';
  try { result.textContent = JSON.stringify(await request(path), null, 2); }
  catch (error) { result.textContent = error.message; }
}
document.querySelector('#refresh').addEventListener('click', () => inspect('/api/status'));
document.querySelector('#dns').addEventListener('click', () => inspect('/api/dns'));
request('/api/eventos').then(data => {
  const grid = document.querySelector('#events'); grid.replaceChildren();
  for (const event of data.events) {
    const card = document.createElement('article'); card.className = 'card';
    for (const [tag, cls, text] of [['span', 'tag', event.category], ['h3', '', event.title], ['p', '', event.description], ['div', 'when', event.date], ['small', '', event.place]]) {
      const el = document.createElement(tag); el.className = cls; el.textContent = text; card.appendChild(el);
    }
    grid.appendChild(card);
  }
}).catch(error => { document.querySelector('#load-error').textContent = 'Não foi possível consultar os eventos: ' + error.message; });
