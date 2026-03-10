# Study Planner - Project Overview & Architecture

## Project Purpose

Study Planner is an AI-powered, Django-based learning management system that helps students create intelligent study schedules, track learning progress, generate assessments, and receive personalized tutoring. It leverages machine learning for schedule optimization and AI for content summarization, question generation, and tutoring.

---

## 🏗️ Overall Architecture

```
study-planner-latest/
├── study_planner/          # Django Project Root
│   ├── accounts/          # User Authentication & Profiles
│   ├── subjects/          # Course/Subject Management
│   ├── exams/             # Quizzes, Exams, Progress Tracking
│   ├── scheduler/         # AI-Powered Study Scheduling (ML)
│   ├── materials/         # Study Materials & Processing
│   ├── assistant/         # AI Chatbot Tutor
│   └── manage.py
├── colab-model-training/   # ML Model Training Scripts
├── requirements.txt
└── .env
```

---

# 📱 Applications & Functionality

## 1. ACCOUNTS APP 👤

### Purpose
User authentication, registration, and profile management

### Models

```
User (Custom Auth Model)
  ├── email (unique, primary login field)
  ├── first_name, last_name
  ├── password (hashed)
  └── is_staff, is_superuser, is_active

StudentProfile (One-to-One with User)
  ├── learning_pace [slow/medium/fast]
  ├── email_notifications (bool)
  └── push_notifications (bool)
```

### Key Views

- login_view: Email-based authentication with "Remember Me" option
- register_view: Sign up with learning pace preference + auto-creates StudentProfile
- settings_view: Update personal info, email, learning pace, and notification settings

### Features

- Email-based login (username removed for simplicity)
- Custom UserManager for email authentication
- Session management (14-day remember me)
- Student profile preferences for personalization

---

## 2. SUBJECTS APP 📖

### Purpose
Create and manage subjects/courses and their chapters with content

### Models

```
Subject
  ├── user (FK → User)
  ├── name (course name)
  ├── code (course code)
  ├── difficulty [1-Easy, 2-Medium, 3-Hard]
  ├── created_at
  └── get_user_progress() → calculates mastery %

Chapter
  ├── subject (FK → Subject)
  ├── chapter_number (auto-incremented per subject)
  ├── title
  ├── note_file (PDF upload)
  ├── summary (AI-generated JSON summary)
  ├── is_completed
  └── is_not_pdf (for text-based chapters)

Question
  ├── chapter (FK → Chapter)
  ├── text (question content)
  ├── options_text (JSON: A/B/C/D options)
  └── correct_answer (A/B/C/D)
```

### Key Views

- subjects_list_view: List user's subjects with progress, filtering, and search
- add_subject_view: Create new subject with difficulty level
- edit_subject_view: Modify subject details
- delete_subject_view: Remove subject and its data
- subject_detail_view: View chapters and progress with mastery indicators

### ML Integration

**Question Generation from PDFs**
- Uses `question_generator.py` to extract text and create MCQs

**AI Summary Generation**
- Deepseek API processes PDFs via OCR.space
- Generates structured summaries

---

## 3. EXAMS APP 📝

### Purpose
Quiz management, exam attempts, and learning progress tracking

### Models

```
Exam_time_table
  ├── user (FK → User)
  ├── subject (FK → Subject)
  └── exam_date

Exam
  ├── subject (FK → Subject)
  ├── exam_name, exam_date, exam_time
  ├── duration_minutes
  ├── total_marks, weightage
  └── is_completed

ExamAttempt
  ├── user (FK → User)
  ├── subject (FK → Subject)
  ├── score, total_possible
  └── completed_at (timestamp)

ChapterProgress
  ├── user (FK → User)
  ├── chapter (FK → Chapter)
  ├── summary_viewed (bool)
  ├── questions_generated (bool)
  ├── quiz_completed (bool)
  ├── is_mastered (bool) → True if all correct
  ├── updated_at
  └── progress_percentage (calculated property: % of completed steps)
```

### Key Views

- start_exam_view: Load full subject exam with all questions
- chapter_quiz_view: Load chapter-specific quiz
- submit_exam_view: Calculate score, save ExamAttempt, show results with breakdown
- submit_chapter_quiz: Same as exam but updates ChapterProgress.is_mastered

### Features

- Tracks multiple quiz attempts per subject
- Chapter-level mastery tracking
- Progress percentage = (steps completed / total steps) × 100
- Automatic ExamAttempt records with timestamps

---

## 4. MATERIALS APP 📚

### Purpose
Upload, process, and extract content from study materials

### Models

```
StudyMaterial
  ├── subject (FK → Subject)
  ├── chapter (FK → Chapter, nullable)
  ├── title
  ├── material_type [pdf/handwritten/video/other]
  ├── file (upload to 'materials/')
  ├── extracted_text
  └── uploaded_at

ExtractedQuestion
  ├── material (FK → StudyMaterial)
  ├── question_text
  ├── difficulty (int: 1-3)
  ├── times_practiced
  ├── success_rate (float: 0.0-1.0)
  └── created_at
```

### Key Views

- materials_list_view: Show all uploaded materials grouped by chapter with statistics
- upload_material_view: File upload interface
- process_ai_view: OCR.space API → Deepseek AI → Summarize + Save

### AI Processing Pipeline

1. OCR.space API: Converts PDF images to text (handles multiple pages)
2. Deepseek API: Cleans OCR text + generates academic summary
3. Storage: Saves summary back to Chapter model

---

## 5. SCHEDULER APP ⏱️

### Purpose
AI-powered study scheduling and learning management

### Models

```
TimetableEntry
  ├── user (FK → User)
  ├── day [MON-SUN]
  ├── subject (string: subject name)
  ├── start_time, end_time
  ├── is_break (bool)
  └── unique_together: (user, day, start_time)

StudySchedule
  ├── user (FK → User)
  ├── date, start_time, end_time
  ├── subject (FK → Subject)
  ├── chapter (FK → Chapter, nullable)
  ├── task_type [study/revision/practice/exam]
  ├── priority (1-5, lower = higher)
  ├── generated_by_ai (bool)
  ├── is_completed (bool)
  ├── reminder_sent (bool)
  └── created_at

StudyLog
  ├── user (FK → User)
  ├── subject (FK → Subject)
  ├── start_time, end_time
  └── duration_minutes (int)
```

### Key Views

- dashboard_view: Main hub showing:
  - Today's timetable + study sessions
  - Daily progress (% completed tasks)
  - Global stats: total study hours, average exam score
  - Per-subject stats: hours studied, avg performance, chapters mastered

---

# 🤖 ML Integration - Study Schedule Optimization

### Model Type

RandomForestRegressor (100 trees, max_depth=10)

### Input Features

- difficulty (1-3): Subject difficulty level
- available_hours (1-4): Hours user can study today
- days_left (3-45): Days until exam
- previous_score (30-90): Historical exam performance

### Output Predictions (3 values)

- time_alloc (1-6 hours): Recommended study hours
- priority (1-5): Task urgency level
- revision_freq (int): How many times to revise

### Training Logic

From `colab-model-training/study_planner_schedule.py`

```
500 synthetic samples with rule-based targets:
- Difficulty heavily weights time allocation
- Days until exam creates urgency boost
- Low previous scores increase priority
- Easy subjects far away get low priority
```

### Usage in Dashboard

```
model = joblib.load("scheduler/ml_models/study_planner.pkl")
prediction = model.predict([[difficulty, available_hours, days_left, prev_score]])

# Returns: [time_hours, priority, revision_count]
```

---

## 6. ASSISTANT APP 🤖

### Purpose
AI-powered chatbot tutor providing subject-specific help

### Models

```
ChatSession
  ├── user (FK → User)
  ├── subject (FK → Subject)
  └── created_at

ChatMessage
  ├── session (FK → ChatSession)
  ├── role [user/ai]
  ├── content (message text)
  └── created_at
```

### Key Views

- chat_view: Display chat interface with message history

### AI Tutor Logic

```
1. get_subject_context()
   └─ Extract summaries from first N chapters (max 2000 chars)

2. find_relevant_summary()
   └─ Keyword matching to find most relevant chapter

3. deepseek_chat()
   ├─ System prompt: "You are an expert tutor. Answer based on syllabus."
   ├─ Include subject context (summaries)
   ├─ Temperature: 0.3 (factual, consistent)
   ├─ Max tokens: 250 (concise answers ~120-150 words)
   └─ Guidelines:
      - Answer based on provided syllabus
      - Allowed to explain, provide examples
      - If unrelated to syllabus → "Not in your syllabus"
      - Keep tone encouraging & academic
      - No markdown formatting
```

### Features

- Context-aware answers limited to student's syllabus
- Conversation history persistence
- Subject-specific chat sessions
- Prevents hallucination via system prompts

---

# 🧠 ML & AI Components Summary

| Component | Type | Purpose | Location |
|---|---|---|---|
| Question Generator | ML + NLP | Extract & rank sentences from PDFs, generate MCQs | subjects/question_generator.py |
| Study Scheduler | RandomForest | Predict study hours, priority, revision frequency | scheduler/ml_models/study_planner.pkl |
| Text Summarizer | LLM (Deepseek) | Clean OCR text, summarize chapters | materials/views.py |
| AI Tutor | LLM (Deepseek) | Answer subject questions contextually | assistant/views.py |
| OCR | API (OCR.space) | Extract text from PDFs | materials/views.py |

---

# 🔌 External APIs & Libraries

```
Requirements:
├── Django 5.x (Framework)
├── OpenAI + Deepseek SDK (LLM)
├── joblib (ML model loading)
├── pdfplumber (PDF parsing)
├── scikit-learn (ML models)
├── nltk (NLP - tokenization)
├── pandas (Data processing)
├── requests (HTTP calls)
├── edge_tts (Text-to-speech)
└── google.genai (Google GenAI)

External APIs:
├── Deepseek Chat API (Summaries, Tutoring)
├── OCR.space API (PDF text extraction)
├── Google GenAI API (Optional)
└── Edge TTS (Audio generation)
```

---

# 📊 Data Flow Diagram

```
User Registration
    ↓
[Accounts App] → Create User + StudentProfile

User Adds Subject
    ↓
[Subjects App] → Create Subject, Chapters

User Uploads Material (PDF)
    ↓
[Materials App] → OCR.Space API → Extract Text
    ↓
    [Deepseek API] → Clean + Summarize
    ↓
    Save to Chapter.summary

User Requests Questions
    ↓
[Subjects App] → question_generator.py
    ↓
    [TF-IDF Model] → Rank Sentences → Generate MCQs
    ↓
    [Save Questions] → Question model

Dashboard Load
    ↓
[Scheduler App] → ML Model (study_planner.pkl)
    ↓
    Predict: [time_alloc, priority, revision_freq]
    ↓
    Display recommendations + progress stats

User Takes Quiz
    ↓
[Exams App] → Calculate Score → Create ExamAttempt
    ↓
    Update ChapterProgress.is_mastered
    ↓
    Show Results

User Asks Question
    ↓
[Assistant App] → Get subject context
    ↓
    [Deepseek API] → Answer based on syllabus
    ↓
    Save ChatMessage → Display response
```

---

# 🎯 Key Features & Workflow

## Student Learning Flow

1. Register with learning pace preference
2. Add Subjects with difficulty levels
3. Upload PDFs → System auto-summarizes + extracts questions
4. View Summaries and study materials
5. Take Chapter Quizzes → Unlock mastery badges
6. Ask AI Tutor subject-specific questions
7. Check Dashboard for ML-powered study recommendations
8. Track Progress with visual stats (hours, scores, mastery %)

---

# 🔐 Security & Design Patterns

- Email-based Authentication (no username)
- User Isolation: All queries filtered by user=request.user
- Model Validation: Unique constraints on user-subject combinations
- CSRF Protection: Django built-in (except explicit exemptions)
- API Key Management: .env file for secrets (Deepseek, OCR.space)

---

# 🚀 Deployment Notes

- ML Model Storage: Pickled model at `scheduler/ml_models/study_planner.pkl`
- File Uploads: PDFs uploaded to `chapters/notes/` and `materials/`
- Session Management: Configurable expiry (14 days with "Remember Me")
- Database: Django ORM (supports PostgreSQL, MySQL, SQLite)
