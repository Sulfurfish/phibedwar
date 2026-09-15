# Phigros Bed War 

A **Phigros "Bed War" mode** match assistant built with Python and Tkinter. It offers referees a program to manage match flow — including HP tracking, damage settlement, item system, and more.

> This is a community-made tool for fan-organized matches. Not affiliated with Phigros or Pigeon Games.

---

## Rules Overview

The following is a summary of the core rules this tool is based on:

### General

- The match is a **team-vs-team** competition, with **3 players per team**.we recommend 3-4 teams.
- Before the match starts, each of the three team members picks one song as their **Personal Song** from a given constant range, and the team picks one **Bed Song** — 4 songs for a team in total. Both Personal Songs and the Bed Song have HP.
- Once the match begins, players attack **other teams' Bed Songs and Personal Songs** by playing them, dealing damage based on their scores.
- **When a player's Personal Song is destroyed, the player is muted (knocked out) for 5 minutes. A player is eliminated when their team's Bed Song is destroyed AND their Personal Song's HP reaches zero.**
- Keep an eye on items spawning during the match — they might help you win!
- When **a team's bed isn't broken**,the player'HP in the team **will immediately return to 5** after his/her HP reaches 0  
### Song Selection Phase

- The 1 hour before the match is the **song selection phase**, lasting **20 minutes**. Each team picks one Bed Song (constant **15.5–15.9**) with **20 HP**.
- Each member picks a Personal Song based on their RKS:

| Tier | RKS Range | Personal Song Constant |
| ---- | ----------------- | ---------------------- |
| A | RKS < 14.00       | 16.7 – 16.9 |
| B | RKS 14.00 – 14.99 | 16.4 – 16.6 |
| C | RKS 15.00 – 15.49 | 16.0 – 16.3 |
| D | RKS 15.50 – 15.99 | 15.5 – 15.9 |
| E | RKS 16.00 – 16.39 | 15.0 – 15.4 |
| F | RKS 16.40 – 16.69 | 14.5 – 14.9 |
| G | RKS 16.70 – 16.99 | 14.0 – 14.4 |

- Each Personal Song has **5 HP**. When the Bed Song is destroyed, the Personal Songs **gain +5 HP and +5 max HP**.
- After song selection, referees need ~10 minutes for verification and preparation.

### Damage Rules

Damage dealt by playing an enemy Personal/Bed Song:

| Rank | Damage |
| -------- | ---------- |
| V | 4 |
| S | 3 |
| A | 2 |
| B | 1 |
| FC/AP | +1 bonus |

- When submitting a score, send the screenshot to the match group, **@ the referee, and include your team name and the target team name. The screenshot must show the current timestamp.**
- the upper rule can be optimized according to your realistic needs.
### Ultimate Death Phase

- 1 hour into the match, the **Sudden Death phase** begins: **max HP of all Personal Songs and Bed Songs is reduced to 5**.
- 1 hour is not strictly ruled,you can change the time according to your realistic needs.
### Item System

- A random item spawns every **8–10 minutes**, with random unlock conditions. If nobody claims an item before the next one spawns, the unclaimed item is discarded.
- To claim an item, **@ the referee with a score screenshot and state that you're claiming the item**. Claimed items can be saved for later — **@ the referee again** to activate an item. Items can be stacked.

| Item | Effect  |
| -------------- | ------------------------------------------------------------------- |
| Mute Card | Mute one team for 5 minutes |
| Revive Card | Revive a teammate with 5 HP |
| Nerf Card | Reduce any player's Personal Song constant by up to 1.0 (user picks the song) |
| Damage x2 Card | Double the damage of your next attack |
| Heal Card | Restore 8 HP to a chosen player or Bed Song |
| Shield Card | Make a chosen player or Bed Song immune to the next instance of damage |
| Attack Card | Deal 5 damage to a chosen player or Bed Song |

### Fair Play

- Cheating (boosting, faking RKS, proxy playing, etc.) is strictly forbidden. All scores must be achieved during the match window. Violations may result in **point deductions or disqualification**.
- Each member of the winning team receives **5 points**.

---

## 🛠️ Requirements

- Python 3.8+ (standard library only — no extra dependencies)
- pyinstaller (recommended)

## 📦 Usage
  There are two ways to run this project: **run it directly with Python** (recommended if you have Python installed or use an IDE), or **build a standalone executable with PyInstaller** (no Python required on the target machine).

### Option 1: Run with Python IDE

**Requirements:** Python 3.8+ (Tkinter is included in the standard library on Windows and macOS official builds; on Linux you may need to install it, e.g. `sudo apt install python3-tk`).
**Run from an IDE (PyCharm / VS Code / IDLE, etc.)**

1. Clone or download the repository and open the project folder in your IDE.
2. (Optional) Create and activate a virtual environment.

### Option 2: using pyinstaller 
