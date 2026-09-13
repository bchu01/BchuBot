# BchuBot setup (new device)

GitHub has the code only. The model, Python packages, Google login, and memories are not in the repo.

This is a local CLI on the machine that runs it. It is not a remote server yet.

## 1. Install

- Git
- Python 3.10+
- [Ollama](https://ollama.com)

```bash
ollama pull qwen3:8b
```

Keep Ollama running. `qwen3:8b` needs roughly 8GB+ free RAM.

## 2. Clone and install packages

```bash
git clone https://github.com/bchu01/BchuBot.git
cd BchuBot
python3 -m venv BchuBot-env
source BchuBot-env/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

On Windows: `BchuBot-env\Scripts\activate`

Do not copy `BchuBot-env` from another computer. Recreate it.

## 3. Private files (`~/.bchubot`)

```bash
mkdir -p ~/.bchubot
```

| File | Required | Notes |
|---|---|---|
| `~/.bchubot/google_credentials.json` | For Calendar / Tasks | Copy from the old machine, or download the Desktop OAuth client JSON again |
| `~/.bchubot/google_token.json` | Created on first login | Prefer a fresh sign-in on this device |
| `~/.bchubot/memory.sqlite` | Optional | Copy only if you want the same long-term memories |

Never commit these files.

**Google (first time on this device)**

1. Calendar API and Tasks API enabled in the same Google Cloud project.
2. OAuth consent screen: add your Google account as a test user.
3. Desktop OAuth client JSON saved as `~/.bchubot/google_credentials.json`.
4. The first calendar/task request opens a browser **on this device**. After you accept, `google_token.json` is written.

Headless machines (no browser) will get stuck on that login.

## 4. Run

```bash
source BchuBot-env/bin/activate
python main.py
```

Try: `What time is it?` then `What's the weather in Boston?`

For Calendar: `What's on my calendar today?`  
For memory: `Remember that I prefer oat milk.` then restart and ask again.

Writes to Calendar/Tasks ask `Allow this action? [y/N]`.

## Checklist

- [ ] Ollama running, `qwen3:8b` pulled
- [ ] venv created, `pip install -r requirements.txt`
- [ ] tests pass
- [ ] `~/.bchubot/google_credentials.json` in place (if you want Google)
- [ ] browser login completed on this device
- [ ] `memory.sqlite` copied only if you want old notes
