const chatContainer = document.getElementById('chatContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

// ارسال بالزر
sendBtn.addEventListener('click', sendMessage);

// ارسال بضغط Enter
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // اضف رسالة المستخدم
    addMessage(message, 'user');
    userInput.value = '';
    sendBtn.disabled = true;

    // مؤشر التحميل
    const loadingId = addMessage('جاري التفكير...', 'loading');

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: message})
        });

        const data = await res.json();
        removeMessage(loadingId);
        addMessage(data.reply || 'عذراً، حدث خطأ.', 'bot');

    } catch (err) {
        removeMessage(loadingId);
        addMessage('تعذر الاتصال بالخادم، أعد المحاولة.', 'bot');
    } finally {
        sendBtn.disabled = false;
    }
}

function addMessage(text, type) {
    const div = document.createElement('div');
    div.className = `message ${type}-msg`;
    div.textContent = text;
    if (type === 'loading') div.id = 'load-' + Date.now();
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return div.id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
