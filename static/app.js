const form = document.getElementById('task-form');
const list = document.getElementById('task-list');
const statusEl = document.getElementById('status');

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? 'status error' : 'status ok';
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('ru-RU');
}

async function api(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

function renderTasks(tasks) {
  list.innerHTML = '';
  if (!tasks.length) {
    list.innerHTML = '<li class="empty">Задач пока нет</li>';
    return;
  }

  tasks.forEach((task) => {
    const li = document.createElement('li');
    li.className = `task ${task.reminded ? 'done' : ''}`;
    li.innerHTML = `
      <div class="meta">
        <strong>${task.title}</strong>
        <p>${task.description || '—'}</p>
        <small>${formatDate(task.due_at_utc)} • ${task.reminded ? 'напоминание отправлено' : 'ожидает отправки'}</small>
      </div>
      <button class="danger" data-id="${task.id}">Удалить</button>
    `;

    li.querySelector('button').addEventListener('click', async () => {
      try {
        await api(`/api/tasks/${task.id}`, { method: 'DELETE' });
        setStatus('Задача удалена.');
        await loadTasks();
      } catch (err) {
        setStatus(`Ошибка удаления: ${err.message}`, true);
      }
    });

    list.appendChild(li);
  });
}

async function loadTasks() {
  try {
    const tasks = await api('/api/tasks');
    renderTasks(tasks);
  } catch (err) {
    setStatus(`Ошибка загрузки списка: ${err.message}`, true);
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const dueAtInput = document.getElementById('due_at').value;
  if (!dueAtInput) {
    setStatus('Выбери дату и время.', true);
    return;
  }

  const payload = {
    title: document.getElementById('title').value.trim(),
    description: document.getElementById('description').value.trim(),
    due_at: new Date(dueAtInput).toISOString(),
  };

  try {
    await api('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    form.reset();
    setStatus('Задача добавлена.');
    await loadTasks();
  } catch (err) {
    setStatus(`Ошибка создания: ${err.message}`, true);
  }
});

loadTasks();
setInterval(loadTasks, 15000);
