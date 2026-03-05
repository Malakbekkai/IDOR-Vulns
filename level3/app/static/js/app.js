// ── Archive Vault UI ──────────────────────────────────────────────

/**
 * Render folder cards into the #folder-grid container.
 * @param {Array} folders  Array of {id, name} objects from the API
 */
function renderFolders(folders) {
  const grid = document.getElementById('folder-grid');
  if (!grid) return;
  grid.innerHTML = '';
  folders.forEach(function(f) {
    const card = document.createElement('a');
    card.className = 'card';
    card.href = '/folder/' + f.id;
    card.innerHTML =
      '<div class="card-icon">◫</div>' +
      '<div class="card-title">' + f.name + '</div>' +
      '<div class="card-meta">FOLDER #' + f.id + '</div>';
    grid.appendChild(card);
  });
}

/**
 * Fetch folders for a given owner and render them.
 * @param {number} ownerId  Numeric user ID
 */
function loadFolders(ownerId) {
  fetch('/folders?owner=' + ownerId)
    .then(function(r) { return r.json(); })
    .then(function(data) { renderFolders(data); })
    .catch(function(e) { console.error('Failed to load folders:', e); });
}

// Initialise on page load — pull owner ID from data attribute
document.addEventListener('DOMContentLoaded', function() {
  const grid = document.getElementById('folder-grid');
  if (grid && grid.dataset.owner) {
    loadFolders(parseInt(grid.dataset.owner, 10));
  }
});
