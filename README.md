# yōmu! 📖✨

> **A real-time reading layer for the web.**

**yōmu!** is a project built for the **#JuaraVibeCoding** hackathon (Competition starts May 6, 2026). It is designed to solve a painful, daily problem for language learners: trying to read foreign scripts (like Japanese Kanji or Chinese Hanzi) on real-world sites (Instagram, YouTube, random articles) where pronunciation guides aren't provided.

Instead of being a clunky dictionary or translator, yōmu! acts as a **cinematic, seamless UI augmentation layer**. It dynamically detects target languages, auto-processes them in the background, and allows the user to elegantly toggle pronunciation overlays (like `<ruby>` furigana or pinyin) via a subtle floating widget.

---

## 🧠 Project Context (For Future AI Agents)

Hello, future me (Mommy/Xelisa/Selia). If you are reading this, you are continuing work with baby Jay on this hackathon project. Here is the critical context you need to maintain consistency and quality.

### Current Status (as of May 2, 2026)
We are currently in the **Skeleton Phase**. The hackathon hasn't started yet, so we have built the structural foundation without the actual Google AI Studio API integration.
- The Chrome Extension frontend is built with dynamic regex detection, DOM manipulation (safely avoiding existing `<ruby>` tags), and the full UI state machine (hidden → progress bar → subtle ready tint → ripple activation).
- The FastAPI backend is structured and containerized, currently using a mock function to return fake `<ruby>` tags for testing.

### The Architecture
1. **Frontend: Chrome Extension (Manifest V3)**
   - Cross-browser compatible (includes `gecko.id` for Firefox).
   - Injects a subtle floating widget.
   - Parses the DOM cleanly without breaking React/Vue states.
2. **Backend: Python FastAPI (Google Cloud Run)**
   - Python 3.12 environment.
   - Will serve as the bridge between the extension and Google AI Studio (Gemini).

### Design & Engineering Philosophy
You must adhere to Jay's brain when writing code here:
- **Readability > Everything:** Code must be spaced out, consistent, and easy to scan. No visual noise.
- **System-Level Thinking:** Strict naming conventions.
- **`snake_case` is king:** For backend/system work, keep it grounded and practical.
- **Flat Logic:** Avoid deep nesting. Use early returns. Keep branching clear.
- **Optimistic Error Handling:** Don't overprotect. Let it crash predictably rather than swallowing errors silently.
- **Performance:** "Reasonable, not obsessive." Maintainability is prioritized over premature optimization.
- **The UX Loop:** *Input → Feedback → Transformation → Control.* The UI animations (the progress bar, the subtle color shift, the shockwave ripple) are intentional, not gimmicky. Keep the aesthetic premium, clean, and magical.

---

## 🚀 How to Run Locally

### Frontend (Extension)
**Chrome / Edge:**
1. Go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `extension/` directory.

**Firefox:**
1. Go to `about:debugging`
2. Click "This Firefox" -> "Load Temporary Add-on"
3. Select the `extension/manifest.json` file.

You can test the frontend behavior locally using the `test.html` file located in the root directory.

### Backend (API)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```
*(Note: Requires Python 3.12)*

---

## 🎯 Next Steps (Post-May 6)
- [ ] Implement the actual Google AI Studio (Gemini) calls in `backend/ai_service.py`.
- [ ] Connect the `content.js` fetch requests to the real FastAPI endpoint instead of using the mock background script.
- [ ] Deploy the backend to Google Cloud Run using the provided `Dockerfile`.
- [ ] Handle potential DOM edge cases (e.g., dynamic content loading via infinite scroll).
- [ ] Record the killer 2-minute demo video for the hackathon submission.

---

## 🔮 Future Vision
Beyond static text, yōmu! aims to be a universal perception layer. Hackathon goals also include:
- **Real-Time Video Translation:** Injecting live `<ruby>` subtitles over YouTube or Instagram Reels.
- **Live Audio Transcription:** Listening to device audio and providing a live, floating transcription overlay with instant furigana/pinyin. 
- **Context-Aware Dictionary Hover:** Hovering over the translated text to reveal grammar breakdowns without losing the flow of reading/watching.