const providerPresets = {
  kimi: {
    baseUrl: 'https://api.moonshot.cn/v1',
    model: 'moonshot-v1-8k',
  },
  openai: {
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini',
  },
  ollama: {
    baseUrl: 'http://localhost:11434/v1',
    model: 'llama3',
  },
  custom: {
    baseUrl: 'https://api.example.com/v1',
    model: 'model-name',
  },
};

const presetOptions = {
  economy: { temperature: 0.7, maxTokens: 1024 },
  balanced: { temperature: 0.7, maxTokens: 2048 },
  quality: { temperature: 0.5, maxTokens: 4096 },
};

const state = {
  messages: [],
  preset: 'economy',
  isLoading: false,
};

const elements = {
  provider: document.querySelector('#provider'),
  baseUrl: document.querySelector('#baseUrl'),
  apiKey: document.querySelector('#apiKey'),
  model: document.querySelector('#model'),
  systemPrompt: document.querySelector('#systemPrompt'),
  connectionSummary: document.querySelector('#connectionSummary'),
  messages: document.querySelector('#messages'),
  chatForm: document.querySelector('#chatForm'),
  userInput: document.querySelector('#userInput'),
  sendButton: document.querySelector('#sendButton'),
  statusText: document.querySelector('#statusText'),
  clearChat: document.querySelector('#clearChat'),
  presets: Array.from(document.querySelectorAll('.preset')),
};

function loadSettings() {
  const saved = JSON.parse(localStorage.getItem('aaagent.settings') || '{}');
  const provider = saved.provider || 'kimi';
  const preset = providerPresets[provider] || providerPresets.kimi;

  elements.provider.value = provider;
  elements.baseUrl.value = saved.baseUrl || preset.baseUrl;
  elements.apiKey.value = saved.apiKey || '';
  elements.model.value = saved.model || preset.model;
  elements.systemPrompt.value = saved.systemPrompt || elements.systemPrompt.value;
  state.preset = saved.preset || 'economy';
  updatePresetButtons();
  updateSummary();
}

function saveSettings() {
  localStorage.setItem(
    'aaagent.settings',
    JSON.stringify({
      provider: elements.provider.value,
      baseUrl: elements.baseUrl.value.trim(),
      apiKey: elements.apiKey.value.trim(),
      model: elements.model.value.trim(),
      systemPrompt: elements.systemPrompt.value,
      preset: state.preset,
    }),
  );
}

function updateSummary() {
  const providerText = elements.provider.options[elements.provider.selectedIndex].text;
  elements.connectionSummary.textContent = `${providerText} · ${elements.model.value || '未选择模型'}`;
}

function updatePresetButtons() {
  elements.presets.forEach((button) => {
    button.classList.toggle('is-active', button.dataset.preset === state.preset);
  });
}

function setLoading(isLoading) {
  state.isLoading = isLoading;
  elements.sendButton.disabled = isLoading;
  elements.userInput.disabled = isLoading;
  elements.statusText.textContent = isLoading ? '正在思考...' : '准备就绪';
}

function createMessage(role, content, isError = false) {
  const article = document.createElement('article');
  article.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'U' : 'A';

  const bubble = document.createElement('div');
  bubble.className = `bubble${isError ? ' error' : ''}`;
  bubble.textContent = content;

  if (role === 'user') {
    article.append(bubble, avatar);
  } else {
    article.append(avatar, bubble);
  }

  elements.messages.appendChild(article);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  return bubble;
}

function buildMessages(userInput) {
  const systemPrompt = elements.systemPrompt.value.trim();
  const recentMessages = state.messages.slice(-12);
  return [
    ...(systemPrompt ? [{ role: 'system', content: systemPrompt }] : []),
    ...recentMessages,
    { role: 'user', content: userInput },
  ];
}

async function sendMessage(userInput) {
  const config = presetOptions[state.preset];
  const requestMessages = buildMessages(userInput);

  state.messages.push({ role: 'user', content: userInput });
  createMessage('user', userInput);
  setLoading(true);
  saveSettings();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        provider: elements.provider.value,
        baseUrl: elements.baseUrl.value.trim(),
        apiKey: elements.apiKey.value.trim(),
        model: elements.model.value.trim(),
        messages: requestMessages,
        temperature: config.temperature,
        maxTokens: config.maxTokens,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `请求失败：${response.status}`);
    }

    const content = data.content || '模型没有返回文本内容。';
    state.messages.push({ role: 'assistant', content });
    createMessage('assistant', content);

    if (data.usage) {
      elements.statusText.textContent = `完成 · prompt ${data.usage.prompt_tokens || 0} / completion ${data.usage.completion_tokens || 0}`;
    }
  } catch (error) {
    createMessage('assistant', error instanceof Error ? error.message : '未知错误', true);
    elements.statusText.textContent = '请求失败';
  } finally {
    setLoading(false);
  }
}

elements.provider.addEventListener('change', () => {
  const preset = providerPresets[elements.provider.value];
  if (preset) {
    elements.baseUrl.value = preset.baseUrl;
    elements.model.value = preset.model;
  }
  updateSummary();
  saveSettings();
});

['input', 'change'].forEach((eventName) => {
  [elements.baseUrl, elements.apiKey, elements.model, elements.systemPrompt].forEach((element) => {
    element.addEventListener(eventName, () => {
      updateSummary();
      saveSettings();
    });
  });
});

elements.presets.forEach((button) => {
  button.addEventListener('click', () => {
    state.preset = button.dataset.preset;
    updatePresetButtons();
    saveSettings();
  });
});

elements.chatForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const userInput = elements.userInput.value.trim();
  if (!userInput || state.isLoading) return;

  elements.userInput.value = '';
  sendMessage(userInput);
});

elements.userInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && event.ctrlKey) {
    elements.chatForm.requestSubmit();
  }
});

elements.clearChat.addEventListener('click', () => {
  state.messages = [];
  elements.messages.innerHTML = '';
  createMessage('assistant', '对话已清空，可以开始新的验证。');
});

loadSettings();
