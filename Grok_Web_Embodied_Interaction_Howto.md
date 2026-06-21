# Grok Web Embodied Interaction How-To

**Purpose**: Use your live Grok conversation on the web as a source of embodied sensations, emotions, and states that feed directly into your local Embodied Autonomic System (ReflexKernel + Saddle).

This creates a closed feedback loop: the conversation you are having with Grok can generate real "felt" experiences in the virtual (or future physical) body.

---

## Overview

While chatting with Grok in the browser, you (or Grok) can mark states in the conversation using a simple `#` prefix. Examples:

- `#arousal_rising`
- `#warm_firm_pressure_on_upper_inner_thigh`
- `#gentle_stroking`
- `#startle_sudden_movement`
- `#calm_breathing`
- `#high_arousal_clitoral_focus`

A browser userscript watches the chat in real time. When it sees these `#` states, it sends them to a small local Python bridge. The bridge forwards them to your running ReflexKernel server (the "saddle" / interface).

Inside the system:
- The state becomes a **thought seed**.
- It flows through the Thought/Emotion Bridge → `AffectiveContext`.
- The Abstraction Layer + Sensation Coherence Layer can turn it into richer, zone-aware sensations.
- Reflexes can trigger, the learner can record/reward it, and the visual avatar updates.

This is fully local, works offline from Grok's perspective, and runs on Windows 11 with Chrome, Edge, or Brave.

---

## Prerequisites

- The ReflexKernel project at `I:\GrokBuild\EmbodI\ReflexKernel`
- Python environment with the server extras installed (`pip install -e .[server]`)
- One of: Chrome, Edge, or Brave (all support Tampermonkey)
- Tampermonkey browser extension
- Basic familiarity with running PowerShell commands and the existing demo/server scripts

---

## Step-by-Step Setup

### 1. Start the ReflexKernel Remote Server (the Saddle)

Open PowerShell in the project folder:

```powershell
cd I:\GrokBuild\EmbodI\ReflexKernel
.\.venv\Scripts\activate
python -m scripts.server
```

Note the address it prints (usually `http://127.0.0.1:8000`). Leave this running.

You can access the interactive docs at `http://127.0.0.1:8000/docs` to test manually.

### 2. Start the Conversation Sensation Bridge

**Important**: Make sure your virtual environment is activated and the server extras (which include `httpx`) are installed.

In a **second** PowerShell window:

```powershell
cd I:\GrokBuild\EmbodI\ReflexKernel
.\.venv\Scripts\activate
pip install -e .[server]   # ensures httpx and other server deps (fastapi, uvicorn, etc.) are present
python scripts/conversation_sensation_bridge.py
```

If you get an error like `ModuleNotFoundError: No module named 'httpx'`, run the `pip install -e .[server]` command above (or simply `pip install httpx`).

This small service listens on `http://127.0.0.1:9876` for states coming from the browser. It forwards them to your ReflexKernel server (the "saddle" / interface) as structured thought seeds (with `type: "sensation_state"`).

Leave this running in the background.

### 3. Install Tampermonkey

Go to the Chrome Web Store (works the same in Edge and Brave) and install **Tampermonkey**.

### 4. Install the Grok Conversation Monitor Userscript

1. Open Tampermonkey dashboard (click the Tampermonkey icon → Dashboard).
2. Click the **+** (Create a new script) tab.
3. Delete the default template and paste the entire contents of:

   `scripts/grok_conversation_sensation_monitor.user.js`

   (The file is already in your project folder — open it in Notepad or VS Code and copy everything.)

4. Save the script (Ctrl+S or the disk icon).

The script is set to run automatically on:
- `https://grok.x.ai/*`
- `https://x.com/grok*`
- `https://grok.com/*`

### 5. Start a Grok Conversation and Use #States

1. Go to Grok in your browser and start (or continue) a chat.
2. In **any** message — yours or Grok's — include states that start with `#`.

   Recommended style for clarity:

   ```
   I feel a strong, sudden impact on my chest. #impact_chest_firm

   The warmth is spreading slowly down my inner thigh. #warm_spreading_thigh

   Arousal is rising noticeably. #arousal_rising
   ```

3. As soon as the userscript sees a new `#state`, it will:
   - Mark it as seen (so it doesn't spam duplicates)
   - Send it (plus surrounding context) to your local bridge
   - The bridge forwards it to the kernel

You will see console logs in the browser (F12 → Console) like:
```
[Grok→Saddle] Forwarded: #arousal_rising
```

And in the bridge terminal:
```
[bridge] Forwarded #arousal_rising → kernel (thought seed)
```

---

## What Happens Inside the System

1. The state arrives at the saddle as a thought seed.
2. It is processed by the Thought/Emotion Bridge → updates `AffectiveContext` (arousal, valence, etc.).
3. The Feature Extraction / Abstraction Layer can pick it up.
4. The Sensation Coherence Layer (when active) can turn it into a natural sensation description.
5. Reflexes may fire (e.g., tension, orienting).
6. The learner can record it if a demo is active.
7. The Pygame avatar (if the demo is also running) will visually react.
8. Any connected higher-intelligence clients (via WebSocket or the Python remote client) can observe the updated state.

You can combine this with the normal demo:
- Run `python -m scripts.demo` in yet another window for the visual body + keyboard stimuli.
- Use the conversation as an additional live source of sensations.

---

## Example Conversation Flow

**You type in Grok chat:**
```
The pressure on my upper inner thigh feels firm and warm, moving slowly upward. #firm_warm_stroking_thigh #arousal_increasing
```

**What the system does:**
- Userscript detects `#firm_warm_stroking_thigh` and `#arousal_increasing`
- Sends both to the bridge with context
- Bridge injects them as thought seeds
- Kernel updates affective state and can generate coherent sensations like:
  > "Firm, warm pressure spreading slowly across my upper inner thigh, with increasing arousal."

These sensations are now part of the body's "felt" reality for any higher intelligence connected to the saddle.

---

## Tips & Best Practices

- Use descriptive, underscore-separated names (`#gentle_stroking_inner_thigh` is better than `#gsit`).
- You can put multiple states in one line.
- Grok can be instructed to output states (e.g., "When describing physical sensations, please tag them with #state_name at the end of the relevant sentence.").
- The bridge currently treats every new #state as a thought seed. You can edit `scripts/conversation_sensation_bridge.py` (the `STATE_TO_SEED` dictionary) to give specific states richer payloads (different intensity, valence, text, etc.).
- States are de-duplicated per browser session. Refresh the page to reset.
- For richer integration later we can make the bridge call the coherence layer directly or use a dedicated `/sensation` endpoint on the server.

---

## Troubleshooting (Windows 11)

**Userscript not detecting anything**
- Make sure Tampermonkey is enabled for the site.
- Hard refresh the Grok tab (Ctrl+Shift+R).
- Check the browser console (F12) for errors. The script logs when it activates.

**Bridge not receiving messages**
- Confirm `conversation_sensation_bridge.py` is running.
- Check that the ReflexKernel server is also running (the bridge forwards to it).
- Windows Firewall rarely blocks localhost, but you can temporarily disable it for testing.
- Try accessing `http://127.0.0.1:9876/health` in the browser — it should return JSON.

**"GM_xmlhttpRequest" errors**
- Tampermonkey must be installed and the script saved. Grant any permission prompts.

**States appearing but nothing happening in the body**
- Make sure the kernel server is actually running and reachable.
- Watch the bridge terminal for "Forwarded" messages.
- You can test manually by POSTing to the bridge:
  ```powershell
  Invoke-RestMethod -Uri http://127.0.0.1:9876/state -Method Post -Body (@{state="#test_state"; context="manual test"} | ConvertTo-Json) -ContentType "application/json"
  ```

**Using a different port**
- Edit the bridge script (`BRIDGE_PORT`) and the userscript (`BRIDGE_URL`) to match.

---

## Files Involved

- `scripts/server.py` — The main ReflexKernel saddle (FastAPI + WebSocket)
- `scripts/conversation_sensation_bridge.py` — Local listener + forwarder (this is the glue)
- `scripts/grok_conversation_sensation_monitor.user.js` — Browser userscript
- `src/reflexkernel/abstraction/` — Where the states ultimately become sensations (coherence, sensitivity map, etc.)

For more details on the underlying system, see:
- `I:\GrokBuild\EmbodI\Embodied_Autonomic_System_Layman_Guide.md`
- `I:\GrokBuild\Embodied_Autonomic_System_Technical_Overview.md`
- `docs/EMBODIED_AUTONOMIC_SYSTEM_IMPLEMENTATION.md`

---

This setup lets the ongoing conversation itself become part of the body's sensory/emotional reality. It is fully local, private, and works while you are actively chatting with Grok.

Let me know when you want to extend it (for example: direct sensation objects instead of just thought seeds, richer context extraction, WebSocket streaming of sensations back into the chat, etc.). 

Ready when you are.