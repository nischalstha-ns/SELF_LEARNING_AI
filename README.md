# JARVIS Voice Assistant

## Setup
```bash
pip install -r requirements.txt
```

## Run

**Option 1: Normal Mode**
```bash
python jarvis.py
```

**Option 2: Background Mode (Recommended)**
```bash
python jarvis_background.py
```
Or double-click `start_jarvis_visible.bat`

**Option 3: Silent Background (No Window)**
Double-click `start_jarvis.bat`

## Auto-Startup
Run this to start JARVIS automatically with Windows:
```bash
python install_startup.py
```

## Hotkeys
- **Ctrl+Shift+J** - Activate/Deactivate JARVIS
- **Ctrl+Shift+Q** - Quit JARVIS

## Features
- **Vision & Face Recognition** - Camera access, face learning, scene description
- **Bilingual** - English & Nepali (नेपाली) with auto-detection
- **Self-Learning AI** - Learns from web and remembers everything
- **Full System Control** - Complete PC automation
- **Always Listening** - Background service with hotkeys

## Commands / आदेशहरू

**Vision & Face Recognition:**
- Who am I seeing / Who do you see
- Learn my face / Remember my face
- Learn face [name]
- Take photo / Take picture
- Show camera / Open camera
- Describe scene / What do you see
- Stop camera

**System Control:
- Volume up/down/mute
- Brightness up/down
- WiFi on/off
- Screenshot
- Lock/Shutdown/Restart/Cancel shutdown
- Battery status
- CPU/Memory/Disk usage
- System info
- Show running apps
- Minimize/Maximize windows
- Empty recycle bin

**App Control:**
- Open/close [app] (Chrome, Notepad, Calculator, Paint, etc.)
- Type [text]
- Press [key]

**File Management:**
- Create folder [name]
- Delete file [name]
- List files
- Copy/Move files

**Web & Knowledge:**
- Search [query]
- Play [video]
- What/Who/Where/When/How/Why [question] - Auto web search & learn
- Tell me about [topic]
- Weather [in city]
- News
- Translate [text]

**Productivity:**
- Write/create note
- Calculate [math expression]
- Remind me to [task]
- What time is it
- What's the date
- Tell me a joke
- Copy clipboard

**Location & Network:**
- Where am I
- IP address
- Weather in [city]

**Learning:**
- Auto-learns from web searches
- Auto-learns from statements ("My name is...")
- Correct me - Updates memory
- Remembers everything permanently
- Context-aware conversations

**Conversation:**
- Always listening mode
- Bilingual (English/Nepali)
- "Stop listening" - Pause (wake with "Hey Jarvis")
- "Stop/Exit" - Quit

## Note
Requires microphone and camera access.

## Vision Setup
For face recognition features:
```bash
pip install opencv-python face-recognition numpy
```
