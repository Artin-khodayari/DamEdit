# 🖍 DamEdit - Python Code Editor

![DamEdit GUI](assets/DamEdit.png)

**DamEdit** (or actull **Damavand Code Editor**) is a lightweight, config-driven Python code editor built with **Tkinter**. It offers **syntax highlighting**, **line numbers**, a **file browser sidebar**, customizable **themes**, and a built-in **search dialog**, providing a minimal yet functional environment for Python development.

---

## 🌟 Features

- 🎨 **Syntax Highlighting**
  - Built-in Python support
  - Load custom language configs (`configs/*.json`)
  - Regex-based or keyword-based highlighting
- 🎨 **Themes**
  - Built-in dark theme
  - Load custom theme JSONs dynamically
  - Reset to default theme
- 📂 **File Management**
  - Open, Save, Save As
  - File sidebar for browsing current directory
- 📝 **Editor Utilities**
  - Line numbers with automatic updates
  - Highlight current line
  - Increment/decrement font size
- 🔍 **Search**
  - Find next/previous in the editor
  - Highlight search matches
- 🖥️ **UI**
  - Toolbar with file, programming language, theme, and find options
  - Scrollbars synchronized with text area and line numbers
  - Cross-platform (Windows, Linux)

---

## 📦 Installation

1. Clone the repository:

```bash
git clone https://github.com/Artin-khodayari/DamEdit.git
cd DamEdit
```

2. Ensure Python 3.10+ is installed.

3. Run the editor:

```bash
python main.py
```

---

## 🖥️ Usage

- **Open a file:** `File → Open` or `Ctrl+O`
- **Save a file:** `File → Save` or `Ctrl+S`
- **Save As:** `File → Save As` or `Ctrl+Shift+S`
- **Change language:** `Language → Load language JSON...`
- **Change theme:** `Theme → Load Theme JSON...`
- **Find text:** `Ctrl+F` or `Find button`
- **Increase/decrease font size:** `Ctrl + / Ctrl -`

The editor automatically detects language config based on file extension. If no config exists, it defaults to Python highlighting for `.py` files.

---

## ⚙️ Configs & Themes

- Place **language configs** in the `configs/` folder (JSON format).

- Language JSON can define:
  - `type`: `"python"` or `"regex"`
  - `keywords`: dictionary of tag → word list
  - `patterns`: regex-based highlighting rules
  - `theme` or `colors`: optional color overrides
  - `extensions`: file extensions it applies to

- **Themes** are JSON files mapping editor tags to hex colors:

```json
{
  "editor_bg": "#1C1B21",
  "editor_fg": "#D8D8D8",
  "control": "#569CD6",
  "string": "#F29E74"
}
```

---

## 🖼 GUI

- Minimal dark-themed design
- Sidebar for file navigation
- Active-line highlighting
- Custom scrollbars and styled buttons
- Separate find window with search controls

---

## 🤝 Contributing

Contributions are welcome!

1. Fork this repository
2. Create a feature branch (`git checkout -b feature-name`)
3. Make your changes
4. Commit (`git commit -am 'Add new feature'`)
5. Push (`git push origin feature-name`)
6. Open a Pull Request

---

## 🧑‍💻 About the Developer

This project is made by [Artin Khodayari](https://github.com/Artin-khodayari).  
You can contact me and report bugs via [Gmail](mailto:ArtinKhodayari2010@gmail.com).

---

## 📄 License

This project is licensed under the [MIT License](https://githu.com/Artin-khodayari/DamEdit/LICENSE).
