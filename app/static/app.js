const form = document.querySelector('#validator-form');
const submitButton = document.querySelector('#submit-button');
const email = document.querySelector('#email');

const views = {
  empty: document.querySelector('#empty-state'),
  loading: document.querySelector('#loading-state'),
  error: document.querySelector('#error-state'),
  results: document.querySelector('#results'),
};

function show(name) {
  Object.entries(views).forEach(([key, element]) => {
    element.classList.toggle('hidden', key !== name);
  });
}

async function post(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map(item => item.msg).join(', ')
      : payload.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return payload;
}

function text(selector, value, fallback = 'Not available') {
  document.querySelector(selector).textContent = value ?? fallback;
}

function render(result) {
  const {profile, compliance, fit} = result;
  const status = compliance.status.toLowerCase();
  const badge = document.querySelector('#status-badge');
  badge.textContent = status;
  badge.className = `badge ${status}`;

  text('#confidence', `Fit ${fit.score}/100 · ${fit.category}`);
  document.querySelector('#fit-fill').style.width = `${fit.score}%`;
  text('#company-name', profile.company);
  const domainLink = document.querySelector('#company-domain');
  domainLink.textContent = profile.domain;
  domainLink.href = `https://${profile.domain}`;
  text('#summary', profile.summary);
  text('#headquarters', profile.headquarters);
  text('#employees', profile.employee_estimate?.toLocaleString());
  text('#business-model', profile.business_model);
  text('#cloud-intensity', profile.cloud_intensity);
  text('#reason', compliance.reason);
  const fitReasons = document.querySelector('#fit-reasons');
  fitReasons.replaceChildren(...fit.reasons.map(value => {
    const item = document.createElement('li');
    item.textContent = value;
    return item;
  }));

  const match = document.querySelector('#match');
  const matchValue = compliance.matched_rule || compliance.possible_match;
  match.textContent = matchValue ? `Match: ${matchValue}` : '';
  match.classList.toggle('hidden', !matchValue);

  const signals = document.querySelector('#signals');
  signals.replaceChildren(...profile.cloud_signals.map(value => {
    const item = document.createElement('li');
    item.textContent = value;
    return item;
  }));
  document.querySelector('#signals-section').classList.toggle('hidden', !profile.cloud_signals.length);

  const sources = document.querySelector('#sources');
  sources.replaceChildren(...profile.sources.map(source => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = source.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = source.title || new URL(source.url).hostname;
    item.append(link, ` — ${source.supports}`);
    return item;
  }));
  document.querySelector('#sources-section').classList.toggle('hidden', !profile.sources.length);
  text('#result-subtitle', `${result.disposition.replaceAll('_', ' ')} · notification ${result.notification_status}`);
  show('results');
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value));
}

function trackerRow(result) {
  const row = document.createElement('tr');
  const detailRow = document.createElement('tr');
  detailRow.className = 'detail-row hidden';
  const detailCell = document.createElement('td');
  detailCell.colSpan = 7;
  detailCell.append(buildTrackerDetail(result));
  detailRow.append(detailCell);

  const expandCell = document.createElement('td');
  const expandButton = document.createElement('button');
  expandButton.type = 'button';
  expandButton.className = 'expand-button';
  expandButton.setAttribute('aria-expanded', 'false');
  expandButton.setAttribute('aria-label', `Show details for ${result.profile.company}`);
  expandButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
  expandButton.addEventListener('click', () => {
    const willOpen = detailRow.classList.contains('hidden');
    detailRow.classList.toggle('hidden', !willOpen);
    expandButton.setAttribute('aria-expanded', String(willOpen));
    expandButton.setAttribute('aria-label', `${willOpen ? 'Hide' : 'Show'} details for ${result.profile.company}`);
  });
  expandCell.append(expandButton);
  row.append(expandCell);

  const values = [
    [result.profile.company, 'table-company'],
    [`${result.lead.name}\n${result.lead.email}`, 'table-contact'],
    [`${result.fit.score} · ${result.fit.category}`, ''],
    [result.compliance.status, ''],
    [result.disposition.replaceAll('_', ' '), ''],
    [formatDate(result.created_at), ''],
  ];
  values.forEach(([value, className], index) => {
    const cell = document.createElement('td');
    if (index === 1) {
      const [name, address] = value.split('\n');
      cell.textContent = name;
      const small = document.createElement('small');
      small.textContent = address;
      cell.append(small);
    } else {
      cell.textContent = value;
    }
    if (index === 2 || index === 4) {
      const pill = document.createElement('span');
      pill.className = index === 2 ? 'score-pill' : `disposition-pill ${result.disposition}`;
      pill.textContent = value;
      cell.textContent = '';
      cell.append(pill);
    } else cell.className = className;
    row.append(cell);
  });
  return [row, detailRow];
}

function element(tag, textValue, className = '') {
  const node = document.createElement(tag);
  if (textValue !== undefined && textValue !== null) node.textContent = textValue;
  if (className) node.className = className;
  return node;
}

function detailList(items) {
  const list = element('ul', null, 'detail-list');
  items.forEach(([label, value]) => {
    const item = element('li');
    if (label) item.append(element('strong', `${label}: `));
    item.append(document.createTextNode(value || 'Not available'));
    list.append(item);
  });
  return list;
}

function buildTrackerDetail(result) {
  const wrapper = element('div', null, 'tracker-detail');
  const company = element('section');
  company.append(element('h3', 'Company research'));
  company.append(element('p', result.profile.summary));
  company.append(element('h4', 'Profile'));
  company.append(detailList([
    ['Domain', result.profile.domain],
    ['Headquarters', result.profile.headquarters],
    ['Employee estimate', result.profile.employee_estimate?.toLocaleString()],
    ['Size band', result.profile.size_band],
    ['Business model', result.profile.business_model],
    ['Cloud intensity', result.profile.cloud_intensity],
    ['Research confidence', `${Math.round(result.profile.confidence * 100)}%`],
  ]));
  if (result.profile.products_services.length) {
    company.append(element('h4', 'Products and services'));
    company.append(detailList(result.profile.products_services.map(value => ['', value])));
  }

  const evidence = element('section');
  evidence.append(element('h3', 'Evidence and signals'));
  evidence.append(element('h4', 'Cloud signals'));
  evidence.append(detailList(
    result.profile.cloud_signals.length
      ? result.profile.cloud_signals.map(value => ['', value])
      : [['', 'No cloud signals identified']]
  ));
  evidence.append(element('h4', 'Research sources'));
  const sources = element('ul', null, 'detail-list');
  (result.profile.sources.length ? result.profile.sources : [{title: '', url: result.lead.website, supports: 'Submitted company website'}]).forEach(source => {
    const item = element('li');
    const link = element('a', source.title || new URL(source.url).hostname);
    link.href = source.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    item.append(link, document.createTextNode(` — ${source.supports}`));
    sources.append(item);
  });
  evidence.append(sources);

  const decision = element('section');
  decision.append(element('h3', 'Decision details'));
  const grid = element('div', null, 'score-grid');
  const scoreParts = [
    ['Company size', result.fit.breakdown.company_size, 35],
    ['Cloud', result.fit.breakdown.cloud_intensity, 40],
    ['Business model', result.fit.breakdown.business_model, 15],
    ['Lead quality', result.fit.breakdown.lead_quality, 10],
  ];
  scoreParts.forEach(([label, value, maximum]) => {
    const card = element('div', null, 'score-item');
    card.append(element('span', label), element('b', `${value}/${maximum}`));
    grid.append(card);
  });
  decision.append(grid);
  decision.append(element('h4', 'Compliance reasoning'));
  decision.append(element('p', result.compliance.reason));
  decision.append(element('h4', 'Lead and delivery'));
  decision.append(detailList([
    ['Job title', result.lead.job_title],
    ['Email alignment', result.email_alignment.replaceAll('_', ' ')],
    ['Compliance confidence', `${Math.round(result.compliance.confidence * 100)}%`],
    ['Matched rule', result.compliance.matched_rule || result.compliance.possible_match],
    ['Report recipient', result.lead.notification_email],
    ['Notification', result.notification_status],
  ]));
  const sendButton = element('button', 'Send email report', 'notify-action');
  sendButton.type = 'button';
  const sendMessage = element('p', '');
  sendMessage.className = 'notify-message';
  sendButton.addEventListener('click', async () => {
    sendButton.disabled = true;
    sendButton.textContent = 'Sending…';
    sendMessage.textContent = '';
    sendMessage.className = 'notify-message';
    try {
      await post(`/api/leads/${result.id}/notify`, {});
      result.notification_status = 'sent';
      sendMessage.textContent = `Report sent to ${result.lead.notification_email || 'the configured sales address'}.`;
      sendMessage.classList.add('success');
      sendButton.textContent = 'Send again';
      await loadTracker();
    } catch (error) {
      sendMessage.textContent = error.message || 'Email delivery failed.';
      sendMessage.classList.add('failure');
      sendButton.textContent = 'Retry email report';
    } finally {
      sendButton.disabled = false;
    }
  });
  decision.append(sendButton, sendMessage);
  wrapper.append(company, evidence, decision);
  return wrapper;
}

async function loadTracker() {
  try {
    const response = await fetch('/api/leads');
    if (!response.ok) return;
    const leads = await response.json();
    const body = document.querySelector('#tracker-body');
    if (leads.length) body.replaceChildren(...leads.flatMap(trackerRow));
  } catch (_) {
    // Tracker loading should never prevent a new submission.
  }
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  submitButton.disabled = true;
  show('loading');
  document.querySelector('#research-step').classList.add('active');
  document.querySelector('#compliance-step').classList.remove('active');
  text('#loading-copy', 'Researching company profile…');

  try {
    const result = await post('/api/leads', {
      name: document.querySelector('#name').value,
      email: email.value,
      company_name: document.querySelector('#company-name-input').value,
      website: document.querySelector('#website').value,
      job_title: document.querySelector('#job-title').value || null,
      notification_email: document.querySelector('#notification-email').value,
    });
    document.querySelector('#research-step').classList.remove('active');
    document.querySelector('#compliance-step').classList.add('active');
    render(result);
    await loadTracker();
  } catch (error) {
    text('#error-copy', error.message || 'An unexpected error occurred.');
    text('#result-subtitle', 'The request was not completed.');
    show('error');
  } finally {
    submitButton.disabled = false;
  }
});

loadTracker();
