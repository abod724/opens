async function sendMessage() {
    const input = document.getElementById("user-input");
    const text = input.value.trim();
    if (!text) return;

    addMessage("user", text);
    input.value = "";

    const res = await fetch("/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: text})
    });

    const data = await res.json();
    addMessage("assistant", data.reply);
}

function addMessage(role, content) {
    const box = document.getElementById("chat-box");
    const div = document.createElement("div");
    div.innerHTML = `<b>${role}:</b> ${content}`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}