# Job Applier

**Job Applier** is a tool for automated job searching and application submission using web scraping and AI.

## 🚀 Features
- 🕵️‍♂️ Job search on popular websites.
- 🤖 Automated application submission.
- 📝 Resume and cover letter generation with AI.
- 📊 Logging and tracking of submitted applications.

## 🔧 Installation
### 1. Clone the repository
```bash
git clone https://github.com/kaliuzhnyi/job_applier.git
cd job_applier
```

### 2. Install dependencies
Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # For Linux/macOS
venv\Scripts\activate  # For Windows
pip install -r requirements.txt
```

### 3. Set up environment variables
A sample `.env` file is provided as `.env.example` in the repository.
Create a `.env` file and specify the necessary API keys and settings.

### 4. Run the script
```bash
python main.py
```

## 🛠️ Technologies Used
- **Python**
- **Selenium / BeautifulSoup** for web scraping
- **AI models** (GPT) for text generation
- **SQLite/PostgreSQL** for data storage

## 📝 License
This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0), which allows others to share and adapt the work, but prohibits commercial use without explicit permission from the author. For details, see [Creative Commons License](https://creativecommons.org/licenses/by-nc/4.0/).
