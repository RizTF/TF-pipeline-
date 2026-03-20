# Guides

---

## Part 1: How to View Your Site Using GitHub Pages

GitHub Pages lets you turn your repo into a live website for free. Here's how:

### Step 1: Open Your Repository
- Open Safari (or any browser) on your iPhone
- Go to: **github.com/RizTF/TF-pipeline-**
- Log in to your GitHub account if needed

### Step 2: Go to Settings
- Tap the **Settings** tab (you may need to scroll the tabs right to find it)
- It has a gear icon

### Step 3: Find the Pages Section
- Scroll down the left sidebar and tap **Pages**
- (On iPhone, you may need to tap the hamburger menu to see the sidebar)

### Step 4: Set Up the Source
- Under **"Build and deployment"**, find **"Source"**
- Select **"Deploy from a branch"**

### Step 5: Pick Your Branch
- Under **"Branch"**, tap the dropdown
- Select: **`claude/enhance-tfpipeline-site-PY81w`**
- Leave the folder as **`/ (root)`**
- Tap **Save**

### Step 6: Wait and Visit
- Wait 1-2 minutes for GitHub to build your site
- Your site will be live at:

```
https://riztf.github.io/TF-pipeline-/
```

- Bookmark this link on your iPhone for easy access!

### Troubleshooting
- **Site not loading?** Wait a few more minutes and refresh
- **404 error?** Make sure the branch name is correct in Settings > Pages
- **Check build status:** Go to the **Actions** tab in your repo to see if the build succeeded

---

## Part 2: Beginner's Guide to Claude Code

Claude Code is an AI coding assistant that runs in your terminal (or on the web). It can read, write, and edit code for you.

### What Can Claude Code Do?
- Write new code and features
- Fix bugs in your project
- Explain how code works
- Run terminal commands
- Create and edit files
- Use git (commit, push, create branches)

### How to Talk to Claude Code

Just type what you want in plain English. Here are examples:

| What you want | What to type |
|---|---|
| Fix a bug | "Fix the login button — it's not working" |
| Add a feature | "Add a dark mode toggle to the navbar" |
| Explain code | "Explain what script.js does" |
| Edit styling | "Make the background blue" |
| Run something | "Run the tests" |
| Git operations | "Commit my changes and push" |

### Useful Slash Commands

Type these directly in the chat:

| Command | What it does |
|---|---|
| `/help` | Shows help info |
| `/clear` | Clears the conversation |
| `/commit` | Commits your changes with a message |

### Tips for Beginners

1. **Be specific** — "Change the title color to red" works better than "make it look nice"
2. **One thing at a time** — Ask for one change, review it, then ask for the next
3. **You're in control** — Claude will ask permission before running risky commands
4. **Say no** — If Claude suggests something you don't want, just say "no, do X instead"
5. **Ask questions** — "What does this file do?" or "Why is this broken?" are great prompts

### Example Conversation

```
You:    "Add a footer to my website that says 'Built by Riz'"
Claude: *reads your index.html, adds a footer, shows you the change*

You:    "Make it sticky at the bottom"
Claude: *updates styles.css to make the footer stick to the bottom*

You:    "Looks good, commit and push"
Claude: *commits the changes and pushes to your branch*
```

### How Claude Code Works Behind the Scenes

1. You type a request
2. Claude reads the relevant files in your project
3. Claude makes edits or runs commands
4. You approve or reject the changes
5. Repeat!

That's it — no setup, no config files, no complex commands. Just describe what you want and Claude does it.
