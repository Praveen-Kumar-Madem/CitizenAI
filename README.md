
# Citizen_AI

Citizen_AI is a Flask-based AI assistant platform designed to help users interact with a conversational AI system for civic and public service purposes. The project integrates IBM WatsonX APIs to deliver intelligent responses and features user authentication, admin dashboard, feedback submission, and a polished frontend interface.

## 🚀 Features

- ✅ User registration and login system
- 💬 AI-powered chat interface using IBM WatsonX
- 🧑‍💼 Admin dashboard to monitor user activity and feedback
- 📝 Feedback submission form
- 📊 User dashboard for personalized experience
- 🎨 Clean and responsive HTML/CSS templates

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS
- **Database**: SQLite
- **AI Integration**: IBM WatsonX APIs

## 📁 Project Structure

```
Citizen_AI_Enhanced/
├── app.py                  # Main Flask application
├── citizen_ai.db           # SQLite database
├── templates/              # HTML templates (views)
├── static/                 # CSS files
├── .env                    # Environment variables
├── requirments.txt         # Python dependencies
```

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Praveen-Kumar-Madem/CitizenAI
   cd Citizen_AI
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirments.txt
   ```

4. **Configure environment**
   - Create a `.env` file in the root folder.
   - Add the following line and replace with your actual IBM API key:
     ```env
     IBM_WATSONX_API_KEY=os.getenv("OPENAI_API_KEY")
5. **Run the application**
   ```bash
   python app.py
   ```

6. Open your browser and visit: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 📸 Screenshots

> Replace this section by pasting screenshots of your app pages (login, chat, dashboard, etc.)

## 🧪 Testing

This project currently supports manual testing by navigating the user interface. Automated test coverage can be added using `pytest` or Flask’s test client.

## 🧑‍💻 Contributing

If you’d like to improve this project, fork the repository, create a new branch, and open a pull request.

## 📄 License

This project is released under the [MIT License](https://opensource.org/licenses/MIT).

## 🙋‍♂️ Author

- **Praveen Madem** — [GitHub Profile](https://github.com/Praveen-Kumar-Madem/CitizenAI)

---

