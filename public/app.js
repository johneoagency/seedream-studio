const form = document.getElementById('form');
const promptEl = document.getElementById('prompt');
const sizeEl = document.getElementById('size');
const goBtn = document.getElementById('go');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');

const drop = document.getElementById('drop');
const fileInput = document.getElementById('file');
const dropHint = document.getElementById('dropHint');
const preview = document.getElementById('preview');
const previewImg = document.getElementById('previewImg');
const removeImg = document.getElementById('removeImg');
const promptLabel = document.getElementById('promptLabel');

// Holds the current reference image as a data URI (or null).
let referenceDataUri = null;

// Shrink a picked image to a max dimension and re-encode, so uploads stay small/fast.
function fileToDataUri(file, maxSize = 1536) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Could not read the file.'));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('That file is not a valid image.'));
      img.onload = () => {
        let { width, height } = img;
        if (width > maxSize || height > maxSize) {
          const scale = maxSize / Math.max(width, height);
          width = Math.round(width * scale);
          height = Math.round(height * scale);
        }
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        canvas.getContext('2d').drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL('image/jpeg', 0.9));
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

async function handleFile(file) {
  if (!file || !file.type.startsWith('image/')) {
    showStatus('Please choose an image file.', { error: true });
    return;
  }
  try {
    referenceDataUri = await fileToDataUri(file);
    previewImg.src = referenceDataUri;
    dropHint.hidden = true;
    preview.hidden = false;
    promptLabel.textContent = 'How should it change the reference?';
    promptEl.placeholder = 'e.g. turn it into a watercolor painting, add a sunset background';
    hideStatus();
  } catch (err) {
    showStatus(err.message, { error: true });
  }
}

function clearReference() {
  referenceDataUri = null;
  fileInput.value = '';
  previewImg.removeAttribute('src');
  preview.hidden = true;
  dropHint.hidden = false;
  promptLabel.textContent = 'Prompt';
  promptEl.placeholder = 'A cinematic ocean wave at sunrise, highly detailed, volumetric light';
}

fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

removeImg.addEventListener('click', (e) => {
  e.preventDefault();
  e.stopPropagation();
  clearReference();
});

['dragover', 'dragenter'].forEach((evt) =>
  drop.addEventListener(evt, (e) => {
    e.preventDefault();
    drop.classList.add('dragover');
  })
);
['dragleave', 'dragend', 'drop'].forEach((evt) =>
  drop.addEventListener(evt, () => drop.classList.remove('dragover'))
);
drop.addEventListener('drop', (e) => {
  e.preventDefault();
  if (e.dataTransfer.files && e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
});

function showStatus(msg, { error = false, loading = false } = {}) {
  statusEl.hidden = false;
  statusEl.className = 'status' + (error ? ' error' : '');
  statusEl.innerHTML = '';
  if (loading) {
    const sp = document.createElement('span');
    sp.className = 'spinner';
    statusEl.appendChild(sp);
  }
  statusEl.appendChild(document.createTextNode(msg));
}

function hideStatus() {
  statusEl.hidden = true;
}

function addResult(url, prompt) {
  const card = document.createElement('div');
  card.className = 'card';

  const img = document.createElement('img');
  img.src = url;
  img.alt = prompt;
  img.loading = 'lazy';

  const meta = document.createElement('div');
  meta.className = 'meta';

  const pr = document.createElement('span');
  pr.className = 'pr';
  pr.textContent = prompt;
  pr.title = prompt;

  const dl = document.createElement('a');
  dl.className = 'dl';
  dl.href = url;
  dl.target = '_blank';
  dl.rel = 'noopener';
  dl.textContent = 'Open ↗';

  meta.append(pr, dl);
  card.append(img, meta);
  resultsEl.prepend(card);
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = promptEl.value.trim();
  if (!prompt) return;

  goBtn.disabled = true;
  const verb = referenceDataUri ? 'Editing your image' : 'Generating';
  showStatus(verb + '… this can take 10–40 seconds.', { loading: true });

  try {
    const payload = { prompt, size: sizeEl.value };
    if (referenceDataUri) payload.images = [referenceDataUri];

    const resp = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();

    if (!resp.ok) {
      showStatus(data.error || 'Something went wrong.', { error: true });
      return;
    }

    (data.images || []).forEach((url) => addResult(url, prompt));
    hideStatus();
  } catch (err) {
    showStatus('Network error: ' + err.message, { error: true });
  } finally {
    goBtn.disabled = false;
  }
});
