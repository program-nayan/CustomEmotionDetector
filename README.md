# Serenity — AI Wellness Assistant

Serenity is an emotion-aware mental wellness companion designed to provide empathetic support and emotional tracking. Unlike standard chatbots, Serenity uses a **Fusion Prediction Engine** that combines the deep linguistic understanding of **RoBERTa** with the generative capabilities of **Google Gemini** to detect subtle emotional cues and respond appropriately.

Whether you're looking for a safe space to vent, daily emotional analytics, or guided wellness interventions, Serenity is built to listen and understand.

---

## ✨ Key Features

*   **Emotion-Aware Chat**: Real-time detection of 7 key emotional states (**Anger, Disgust, Fear, Happiness, Sadness, Surprise, and Neutral**) integrated into the conversation flow.
*   **Fusion Prediction Engine**: A hybrid AI architecture using custom-tuned RoBERTa models for classification and Gemini for contextual response generation.
*   **Personalized Dashboard**: Track your emotional journey with daily and weekly analytics, visualizing trends over time.
*   **Secure Authentication**: Private accounts with encrypted data storage to ensure your reflections stay yours.
*   **Crisis Awareness**: Built-in protocols to detect high-stress signals and provide supportive resources.
*   **Responsive Web UI**: A soothing, modern interface designed for both desktop and mobile use.

---

## 🛠️ Tech Stack

*   **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
*   **AI/ML**: [PyTorch](https://pytorch.org/), [HuggingFace Transformers](https://huggingface.co/docs/transformers/index), [Google Generative AI](https://ai.google.dev/)
*   **Database**: SQLite with [SQLAlchemy](https://www.sqlalchemy.org/)
*   **Frontend**: Vanilla HTML5, CSS3, and JavaScript (served via FastAPI)
*   **Containerization**: [Docker](https://www.docker.com/)

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.10 or higher
*   A Google Gemini API Key (Get one [here](https://aistudio.google.com/app/apikey))

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/CustomEmotionDetector.git
    cd CustomEmotionDetector
    ```

2.  **Set up a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables**:
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_api_key_here
    SECRET_KEY=your_random_secret_string
    ```

### Running the App

You can start the server directly using the helper script:
```bash
python run_server.py
```
The application will be available at `http://localhost:8000`.

---

## 📂 Project Structure

```text
.
├── api/                   # FastAPI application logic
│   ├── core/              # Logger and core utilities
│   ├── frontend/          # HTML/CSS/JS assets
│   ├── routes/            # API endpoints (Auth, Chat, Dashboard)
│   ├── app.py             # Main FastAPI entry point
│   └── database.py        # SQLAlchemy models and DB setup
├── src/                   # AI Core logic
│   ├── predictor/         # RoBERTa + Gemini Fusion logic
│   └── components/        # Reusable AI components
├── custom_roberta_.../    # Trained model checkpoints
├── Data/                  # Local datasets and training files
├── logs/                  # Application logs
├── Dockerfile             # Container configuration
└── run_server.py          # Entry point script
```

---

## 🐳 Docker Deployment

If you prefer using Docker, you can build and run the containerized version:

```bash
# Build the image
docker build -t serenity-wellness .

# Run the container
docker run -p 8000:8000 --env-file .env serenity-wellness
```

---

## 📈 API Endpoints (Short Reference)

*   `GET /`: Serves the landing page.
*   `POST /api/auth/register`: Create a new user account.
*   `POST /api/auth/login`: Authenticate and receive a session token.
*   `POST /api/chat/message`: Send a message and get an emotion-aware response.
*   `GET /api/dashboard/stats`: Fetch emotional trend data for the user.
*   `GET /api/health`: Basic service health check.

---

## 📝 Note on Models
The project relies on pre-trained weights stored in `custom_roberta_multitask_final`. Ensure these directories are present and contain the `config.json` and `pytorch_model.bin` files for the emotion classifier to function correctly.

---

## 🤝 Contributing
Contributions are welcome! If you find a bug or have a feature suggestion, feel free to open an issue or submit a pull request.

---

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
