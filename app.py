import json
import os
import pickle
import sqlite3
import urllib.error
import urllib.request
from functools import wraps

import pandas as pd
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key")

MODEL_PATH = "model.pkl"
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "career_guidance.db")
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")

with open(MODEL_PATH, "rb") as f:
    model_data = pickle.load(f)

model = model_data["model"]
model_columns = model_data["columns"]

GOVERNMENT_JOBS = {
    "SSC MTS": {
        "eligibility": "10th pass, age 18-25 years",
        "description": "Multi-Tasking Staff recruitment through SSC for non-technical posts.",
    },
    "Police": {
        "eligibility": "10th or 12th pass, physical fitness and age requirements vary by state",
        "description": "State or central police recruitment with basic education and fitness criteria.",
    },
    "SSC CHSL": {
        "eligibility": "12th pass, age 18-27 years",
        "description": "Combined Higher Secondary Level exam for clerical and data entry jobs.",
    },
    "Railways": {
        "eligibility": "10th or 12th pass depending on the post, age 18-30 years",
        "description": "Railway recruitment for technical and non-technical positions.",
    },
    "UPSC": {
        "eligibility": "Graduate degree, age 21-32 years depending on category",
        "description": "Civil Services exam for IAS, IPS and other administrative services.",
    },
    "SSC CGL": {
        "eligibility": "Graduate degree, age 18-32 years",
        "description": "Common Graduate Level exam for central government group B and C posts.",
    },
    "Banking": {
        "eligibility": "Graduate degree, age 20-28 years",
        "description": "Bank PO/Clerk exams for various national and regional banks.",
    },
}

CAREER_CATEGORIES = {
    "Software Engineer": "Technology",
    "Business Analyst": "Business",
    "Musician": "Arts",
    "Fitness Coach": "Sports",
    "Teacher": "Education",
    "Doctor": "Health",
    "Civil Engineer": "Engineering",
    "Graphic Designer": "Design",
    "Journalist": "Media",
    "Data Scientist": "Technology",
    "Architect": "Design",
    "Lawyer": "Law",
    "Digital Marketer": "Business",
    "Chef": "Hospitality",
    "Nurse": "Health",
    "Civil Servant": "Government",
    "Bank PO": "Government",
    "Research Scholar": "Academics",
    "Content Creator": "Media",
    "HR Specialist": "Business",
    "UX Designer": "Design",
    "Event Manager": "Business",
    "Environmental Scientist": "Science",
}

CAREER_RESOURCES = {
    "Software Engineer": {
        "courses": ["Python Programming", "Data Structures & Algorithms", "Web Development Bootcamp"],
        "skills": ["Programming", "Problem Solving", "System Design", "Version Control (Git)"],
        "certifications": ["AWS Cloud Practitioner", "Meta Back-End Developer", "Google IT Automation"],
        "packages": ["Fresher: 4-8 LPA", "Mid-level: 10-18 LPA", "Advanced: 20+ LPA"],
        "internships": ["Software Developer Intern", "QA Automation Intern", "Backend Intern"],
        "roadmap": [
            "Build coding fundamentals and complete 2 mini projects.",
            "Learn DSA and solve interview-style coding problems daily.",
            "Build portfolio projects and apply for internships/jobs.",
        ],
    },
    "Data Scientist": {
        "courses": ["Statistics for Data Science", "Machine Learning Basics", "Python for Data Analysis"],
        "skills": ["Statistics", "Machine Learning", "Data Visualization", "Python/SQL"],
        "certifications": ["Google Data Analytics", "IBM Data Science Professional", "TensorFlow Developer"],
        "packages": ["Fresher: 5-10 LPA", "Mid-level: 12-22 LPA", "Advanced: 25+ LPA"],
        "internships": ["Data Analyst Intern", "ML Intern", "Business Intelligence Intern"],
        "roadmap": [
            "Strengthen math, statistics, and Python basics.",
            "Build ML models on real datasets and document results.",
            "Create an end-to-end data portfolio and target analyst/DS internships.",
        ],
    },
    "Business Analyst": {
        "courses": ["Excel & Business Analytics", "SQL for Analysis", "Power BI / Tableau"],
        "skills": ["Data Interpretation", "SQL", "Dashboarding", "Business Communication"],
        "certifications": ["CBAP (Foundation Path)", "Microsoft Power BI", "Google Project Management"],
        "packages": ["Fresher: 4-7 LPA", "Mid-level: 8-15 LPA", "Advanced: 18+ LPA"],
        "internships": ["Business Analyst Intern", "Operations Intern", "Consulting Intern"],
        "roadmap": [
            "Learn spreadsheets, SQL, and data storytelling.",
            "Practice case studies and business problem framing.",
            "Create dashboards and apply for analyst roles.",
        ],
    },
    "Doctor": {
        "courses": ["NEET Preparation Foundation", "Biology Mastery Program", "Medical Ethics Basics"],
        "skills": ["Clinical Reasoning", "Patient Communication", "Biology Fundamentals", "Discipline"],
        "certifications": ["BLS/ACLS (later stage)", "Medical Research Workshops", "Clinical Skills Training"],
        "packages": ["Internship stipend: role-dependent", "Junior doctor: 6-12 LPA", "Specialist: 15+ LPA"],
        "internships": ["Hospital Internship", "Clinical Observer", "Medical Camp Volunteer"],
        "roadmap": [
            "Focus on PCB fundamentals and exam strategy.",
            "Follow mock-test routines and weak-topic revision.",
            "Prepare for admissions, counseling, and early clinical exposure.",
        ],
    },
    "Graphic Designer": {
        "courses": ["Adobe Photoshop/Illustrator", "UI/UX Fundamentals", "Brand Identity Design"],
        "skills": ["Typography", "Branding", "Visual Communication", "Digital Design Tools"],
        "certifications": ["Adobe Certified Professional", "Google UX Design", "Graphic Design Specialization"],
        "packages": ["Fresher: 3-6 LPA", "Mid-level: 7-12 LPA", "Advanced: 15+ LPA"],
        "internships": ["Creative Agency Intern", "Freelance Design Intern", "Social Media Design Intern"],
        "roadmap": [
            "Master design principles and core tools.",
            "Build a strong portfolio with branding and social projects.",
            "Take internships/freelance projects and move into specialization.",
        ],
    },
    "Teacher": {
        "courses": ["Teaching Methodology", "Classroom Management", "Educational Psychology"],
        "skills": ["Public Speaking", "Subject Expertise", "Mentoring", "Lesson Planning"],
        "certifications": ["B.Ed / D.El.Ed", "CTET/TET Preparation", "Child Development Training"],
        "packages": ["Entry-level: 2.5-5 LPA", "Mid-level: 5-9 LPA", "Advanced: 10+ LPA"],
        "internships": ["School Teaching Intern", "Tutoring Assistant", "NGO Education Volunteer"],
        "roadmap": [
            "Build strong fundamentals in your chosen subject.",
            "Gain classroom exposure through internships/tutoring.",
            "Clear teaching eligibility exams and apply to institutions.",
        ],
    },
    "Civil Engineer": {
        "courses": ["Structural Analysis", "AutoCAD & STAAD.Pro", "Construction Management"],
        "skills": ["Design Basics", "Surveying", "Project Planning", "Site Supervision"],
        "certifications": ["AutoCAD Certification", "PMP Foundation", "Revit Structure"],
        "packages": ["Fresher: 3-6 LPA", "Mid-level: 7-13 LPA", "Advanced: 16+ LPA"],
        "internships": ["Site Engineer Intern", "Planning Intern", "Quantity Survey Intern"],
        "roadmap": [
            "Learn core civil concepts and design software.",
            "Work on site visits and internships for practical understanding.",
            "Specialize in structural/project management and scale your career.",
        ],
    },
}

DEFAULT_RESOURCES = {
    "courses": ["Career Foundations", "Communication Skills", "Domain Fundamentals"],
    "skills": ["Communication", "Problem Solving", "Critical Thinking", "Teamwork"],
    "certifications": ["Beginner Domain Certificate", "Soft Skills Certificate"],
    "packages": ["Fresher range: role-dependent (2.5-8 LPA)", "Growth depends on specialization and projects"],
    "internships": ["Domain Internship", "Project Internship", "Remote Internship"],
    "roadmap": [
        "Identify your strongest interests and skills.",
        "Complete beginner courses and practical projects in your domain.",
        "Build a profile, gain experience, and apply for internships.",
    ],
}

QUIZ_QUESTIONS = [
    {"id": "q1", "text": "Do you enjoy solving logical problems?", "weights": {"Software Engineer": 2, "Data Scientist": 2}},
    {"id": "q2", "text": "Do you like creative writing or storytelling?", "weights": {"Journalist": 2, "Content Creator": 2}},
    {"id": "q3", "text": "Do you like teaching or guiding others?", "weights": {"Teacher": 3}},
    {"id": "q4", "text": "Do you enjoy designing visuals or interfaces?", "weights": {"Graphic Designer": 3, "UX Designer": 2}},
    {"id": "q5", "text": "Are you interested in medical or healthcare topics?", "weights": {"Doctor": 3, "Nurse": 2}},
    {"id": "q6", "text": "Do you enjoy analyzing data and trends?", "weights": {"Data Scientist": 3, "Business Analyst": 2}},
    {"id": "q7", "text": "Do you enjoy public speaking and communication?", "weights": {"Teacher": 2, "Digital Marketer": 2, "Lawyer": 1}},
    {"id": "q8", "text": "Do you like planning events or coordinating teams?", "weights": {"Event Manager": 3, "HR Specialist": 2}},
    {"id": "q9", "text": "Would you prefer working in government/public services?", "weights": {"Civil Servant": 3, "Bank PO": 2}},
    {"id": "q10", "text": "Do you enjoy experimenting with new ideas or inventions?", "weights": {"Research Scholar": 3, "Civil Engineer": 1}},
    {"id": "q11", "text": "Do you enjoy problem-solving in teams?", "weights": {"Business Analyst": 2, "Software Engineer": 1, "Civil Engineer": 2}},
    {"id": "q12", "text": "Do you enjoy drawing, branding, or typography?", "weights": {"Graphic Designer": 3}},
]


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS assessment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            marks REAL,
            stream TEXT,
            interest TEXT,
            skill TEXT,
            talent TEXT,
            education TEXT,
            predicted_career TEXT NOT NULL,
            confidence_score REAL,
            top_careers_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            age INTEGER,
            gender TEXT,
            background TEXT,
            marks REAL,
            stream TEXT,
            interest TEXT,
            skill TEXT,
            talent TEXT,
            education TEXT,
            career_goal TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    connection.commit()
    connection.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_user():
    return {"current_user": session.get("username")}


def recommend_government_jobs(education):
    education = str(education).strip().lower()
    if education == "10th":
        jobs = ["SSC MTS", "Police"]
    elif education == "12th":
        jobs = ["SSC CHSL", "Railways"]
    elif education == "degree":
        jobs = ["UPSC", "SSC CGL", "Banking"]
    else:
        jobs = []

    return [
        {"name": job, "eligibility": GOVERNMENT_JOBS[job]["eligibility"], "description": GOVERNMENT_JOBS[job]["description"]}
        for job in jobs
    ]


def recommend_internships(skill, interest):
    skill = str(skill).strip().lower()
    interest = str(interest).strip().lower()
    recommendations = []

    if skill == "coding" or interest == "coding" or interest == "technology" or skill == "data":
        recommendations.append("Software / Data Intern")
    if skill == "music" or interest == "music":
        recommendations.append("Music Intern")
    if skill == "sports" or interest == "sports":
        recommendations.append("Fitness Intern")
    if skill == "communication" or interest == "business" or interest == "management":
        recommendations.append("Business Intern")
    if skill == "creativity" or interest in ["dance", "arts", "design", "media"]:
        recommendations.append("Creative Intern")
    if interest in ["health", "medical", "science"]:
        recommendations.append("Healthcare / Science Intern")
    if interest in ["law", "debate", "social studies"]:
        recommendations.append("Legal Intern")
    if interest in ["design", "ux", "graphic"]:
        recommendations.append("Design Intern")
    if interest in ["hospitality", "food", "travel"]:
        recommendations.append("Hospitality Intern")

    return recommendations or ["General Internship"]


def get_career_resources(career):
    return CAREER_RESOURCES.get(career, DEFAULT_RESOURCES)


def calculate_quiz_recommendations(answers):
    max_scores = {}
    for question in QUIZ_QUESTIONS:
        for career, weight in question["weights"].items():
            max_scores[career] = max_scores.get(career, 0) + weight

    scores = {}
    for question in QUIZ_QUESTIONS:
        answer = answers.get(question["id"], "no")
        if answer != "yes":
            continue
        for career, weight in question["weights"].items():
            scores[career] = scores.get(career, 0) + weight

    if not scores:
        scores = {"Software Engineer": 1, "Business Analyst": 1, "Graphic Designer": 1}

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_ranked = ranked[:3]
    top_total = sum(score for _, score in top_ranked) or 1
    top = [{"name": name, "score": score / top_total} for name, score in top_ranked]
    confidence_map = {
        name: min(1.0, score / (max_scores.get(name, score) or 1))
        for name, score in ranked
    }
    return top, confidence_map


def build_quiz_profile(answers):
    yes_ids = {question_id for question_id, value in answers.items() if value == "yes"}

    interests = []
    if {"q1", "q6", "q11"} & yes_ids:
        interests.append("technology")
    if {"q4", "q12"} & yes_ids:
        interests.append("design")
    if "q5" in yes_ids:
        interests.append("health")
    if {"q2", "q10"} & yes_ids:
        interests.append("creative")
    if {"q3", "q7"} & yes_ids:
        interests.append("teaching")
    if "q9" in yes_ids:
        interests.append("government")

    skills = []
    if {"q1", "q6"} & yes_ids:
        skills.append("analysis")
    if {"q4", "q12"} & yes_ids:
        skills.append("visual-design")
    if {"q3", "q7"} & yes_ids:
        skills.append("communication")
    if {"q8", "q11"} & yes_ids:
        skills.append("teamwork")
    if "q10" in yes_ids:
        skills.append("innovation")

    return {
        "interest": ", ".join(interests) if interests else "general",
        "skill": ", ".join(skills) if skills else "general",
        "education": "Not provided (quiz mode)",
    }


def get_user_profile(user_id):
    connection = get_db_connection()
    row = connection.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    connection.close()
    return dict(row) if row else None


def save_user_profile(user_id, profile):
    connection = get_db_connection()
    exists = connection.execute(
        "SELECT user_id FROM user_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if exists:
        connection.execute(
            """
            UPDATE user_profiles
            SET full_name = ?, age = ?, gender = ?, background = ?, marks = ?, stream = ?, interest = ?, skill = ?,
                talent = ?, education = ?, career_goal = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                profile["full_name"],
                profile["age"],
                profile["gender"],
                profile["background"],
                profile["marks"],
                profile.get("stream"),
                profile["interest"],
                profile["skill"],
                profile["talent"],
                profile["education"],
                profile["career_goal"],
                user_id,
            ),
        )
    else:
        connection.execute(
            """
            INSERT INTO user_profiles
            (user_id, full_name, age, gender, background, marks, stream, interest, skill, talent, education, career_goal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                profile["full_name"],
                profile["age"],
                profile["gender"],
                profile["background"],
                profile["marks"],
                profile.get("stream"),
                profile["interest"],
                profile["skill"],
                profile["talent"],
                profile["education"],
                profile["career_goal"],
            ),
        )
    connection.commit()
    connection.close()


def run_prediction(marks_value, stream, interest, skill, talent, education):
    data = {
        "marks": [marks_value],
        "stream": [stream],
        "interest": [interest],
        "skill": [skill],
        "talent": [talent],
        "education": [education],
    }

    df = pd.DataFrame(data)
    df_encoded = pd.get_dummies(df, columns=["stream", "interest", "skill", "talent", "education"])
    df_encoded = df_encoded.reindex(columns=model_columns, fill_value=0)

    career_prediction = model.predict(df_encoded)[0]
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(df_encoded)[0].tolist()
        labels = model.classes_.tolist()
    else:
        labels = [career_prediction]
        probabilities = [1.0]

    ranked_careers = sorted(
        [{"name": label, "score": prob} for label, prob in zip(labels, probabilities)],
        key=lambda item: item["score"],
        reverse=True,
    )
    top_careers = ranked_careers[:3]
    confidence_score = top_careers[0]["score"] if top_careers else 1.0
    return career_prediction, labels, probabilities, top_careers, confidence_score


def call_llm_api(prompt, profile=None):
    if not LLM_API_KEY:
        return None

    system_message = {
        "role": "system",
        "content": (
            "You are a strict career guidance assistant for students. Only answer questions related to student career planning, academics, internships, "
            "government job preparation, entrance exams, skills development, college admissions, and professional pathways. "
            "If the user asks about anything else, politely say that you only help with student career guidance and academic opportunities. "
            "Answer concisely in no more than 10 lines, using short sentences or brief bullet points. Avoid long paragraphs."
        ),
    }

    user_text = prompt
    if profile:
        user_text = f"{prompt}\n\nUser profile:\n{profile}"

    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [system_message, {"role": "user", "content": user_text}],
        "temperature": 0.75,
        "max_tokens": 280,
    }).encode("utf-8")

    request_obj = urllib.request.Request(
        LLM_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            result = json.loads(response_text)
            choices = result.get("choices", [])
            if choices:
                first_choice = choices[0]
                if "message" in first_choice:
                    return first_choice["message"].get("content", "").strip()
                if "text" in first_choice:
                    return first_choice["text"].strip()
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            # Gracefully fall back to rule-based response when API rate limits hit.
            return None
        return None
    except urllib.error.URLError as exc:
        return None

    return None


def is_career_related_question(text):
    text = str(text).strip().lower()
    if not text:
        return False

    career_keywords = [
        "career", "job", "internship", "work", "profession", "education", "study", "college", "university",
        "school", "exam", "skills", "skill", "talent", "stream", "interest", "subject", "course", "degree",
        "training", "placement", "resume", "interview", "admission", "scholarship", "government", "ssc", "upsc",
        "railway", "banking", "business", "management", "marketing", "finance", "software", "coding", "programming",
        "data", "analytics", "science", "engineering", "arts", "music", "dance", "sports", "teacher", "doctor",
        "lawyer", "design", "media", "journalism", "architecture", "hospitality", "nurse", "health",
        "research", "civil service"
    ]
    unrelated_keywords = [
        "movie", "movies", "series", "celebrity", "hollywood", "bollywood", "netflix", "hotstar", "youtube",
        "instagram", "facebook", "twitter", "recipe", "restaurant", "travel", "flight", "hotel", "shopping",
        "fashion", "stock", "politics", "weather", "joke", "funny", "gaming", "game"
    ]

    if any(keyword in text for keyword in unrelated_keywords):
        return False
    return any(keyword in text for keyword in career_keywords)


def llm_chatbot_answer(question):
    if not question:
        return "Please ask a career-related question so I can help you."

    if not is_career_related_question(question):
        return "I can only answer questions about career guidance, student academics, internships, and related opportunities. Please ask something about career planning or education."

    profile = (
        "This user is looking for personalized career guidance, government job recommendations, internship matching, "
        "and advice on academic and creative pathways."
    )
    response = call_llm_api(f"Answer this career guidance question:\n{question}", profile=profile)
    return response or chatbot_answer(question)


def generate_llm_career_plan(career, marks, stream, interest, skill, talent, education):
    prompt = (
        "Create a concise personalized career development plan for a student with the following profile:\n"
        f"- Predicted career: {career}\n"
        f"- Marks: {marks}\n"
        f"- Stream: {stream}\n"
        f"- Interest: {interest}\n"
        f"- Skill: {skill}\n"
        f"- Talent: {talent}\n"
        f"- Education level: {education}\n\n"
        "Provide a 3-part plan: short-term actions, medium-term goals, and long-term preparation. "
        "Keep the answer within 10 lines and avoid long paragraphs. Use simple, actionable points."
    )
    return call_llm_api(prompt)


def chatbot_answer(question):
    text = str(question).strip().lower()
    if not text:
        return "Please ask a career-related question so I can help you."
    if not is_career_related_question(text):
        return "I can only answer student career guidance, education, internship, and government job questions. Please ask something related to career planning or academics."
    if any(term in text for term in ["engineer", "coding", "software", "tech", "data", "analysis"]):
        return "For a technology career, focus on problem solving, coding practice, data skills, and building real projects relevant to your interests."
    if any(term in text for term in ["doctor", "medicine", "medical", "health", "nurse"]):
        return "A healthcare career often requires strong science scores, practical training, and preparation for medical or nursing entrance exams."
    if any(term in text for term in ["musician", "music", "sing", "band"]):
        return "To build a career in music, practice consistently, learn theory and performance skills, and look for internships or ensembles to gain experience."
    if any(term in text for term in ["athlete", "sports", "fitness", "coach", "physical"]):
        return "A sports career benefits from disciplined training, coaching experience, and balancing fitness with nutrition and teamwork."
    if any(term in text for term in ["business", "entrepreneur", "management", "commerce", "marketing", "finance"]):
        return "For business and commerce careers, focus on communication, leadership, analytics, and practical experience through internships and projects."
    if any(term in text for term in ["government", "ssc", "upsc", "railway", "banking", "civil service"]):
        return "Government jobs need preparation for exams, strong general knowledge, and a disciplined study plan tailored to the specific service you want."
    if any(term in text for term in ["internship", "intern"]):
        return "Look for internships in the fields you enjoy, build a strong application, and use those experiences to decide your next academic or career step."
    if any(term in text for term in ["teacher", "education", "school", "teaching"]):
        return "A teaching career requires subject mastery, communication skills, and practice through tutoring, volunteering, or education internships."
    if any(term in text for term in ["design", "graphic", "ux", "creative", "media", "journalism"]):
        return "Creative careers benefit from portfolios, practical projects, and networking with professionals in design, media, or content creation."
    return "I can help with career paths, academic choices, internships, and student opportunities. Please ask about your interests, skills, or future career decisions."


@app.route("/")
@login_required
def home():
    return render_template("index.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]

    if request.method == "POST":
        marks_raw = request.form.get("marks", "").strip()
        age_raw = request.form.get("age", "").strip()
        profile_data = {
            "full_name": request.form.get("full_name", "").strip(),
            "age": int(age_raw) if age_raw.isdigit() else None,
            "gender": request.form.get("gender", "").strip(),
            "background": request.form.get("background", "").strip(),
            "marks": float(marks_raw) if marks_raw else None,
            "interest": request.form.get("interest", "").strip(),
            "skill": request.form.get("skill", "").strip(),
            "talent": request.form.get("talent", "").strip(),
            "education": request.form.get("education", "").strip(),
            "career_goal": request.form.get("career_goal", "").strip(),
        }

        required_fields = [
            profile_data["full_name"],
            profile_data["gender"],
            profile_data["background"],
            profile_data["marks"],
            profile_data["interest"],
            profile_data["skill"],
            profile_data["talent"],
            profile_data["education"],
        ]
        if any(value in [None, ""] for value in required_fields):
            flash("Please fill all required profile fields.", "error")
            return render_template("profile.html", profile=profile_data, history=[])
        if not (0 <= profile_data["marks"] <= 100):
            flash("Marks should be between 0 and 100.", "error")
            return render_template("profile.html", profile=profile_data, history=[])

        save_user_profile(user_id, profile_data)
        flash("Profile saved successfully.", "success")
        return redirect(url_for("profile"))

    profile_data = get_user_profile(user_id)
    connection = get_db_connection()
    rows = connection.execute(
        """
        SELECT predicted_career, confidence_score, marks, interest, skill, education, created_at
        FROM assessment_history
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,),
    ).fetchall()
    connection.close()
    return render_template(
        "profile.html",
        profile=profile_data or {},
        history=[dict(row) for row in rows],
    )


@app.route("/dashboard")
@login_required
def dashboard():
    connection = get_db_connection()
    rows = connection.execute(
        """
        SELECT id, predicted_career, confidence_score, marks, interest, skill, education, created_at
        FROM assessment_history
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],),
    ).fetchall()
    connection.close()
    history = [dict(row) for row in rows]
    return render_template("dashboard.html", history=history)


@app.route("/quiz", methods=["GET"])
@login_required
def quiz():
    if request.args.get("reset") == "1":
        session["quiz_answers"] = {}
        session["quiz_index"] = 0

    if "quiz_answers" not in session:
        session["quiz_answers"] = {}
        session["quiz_index"] = 0

    quiz_index = int(session.get("quiz_index", 0))
    quiz_index = min(max(quiz_index, 0), len(QUIZ_QUESTIONS) - 1)
    question = QUIZ_QUESTIONS[quiz_index]
    return render_template(
        "quiz.html",
        question=question,
        current_index=quiz_index + 1,
        total_questions=len(QUIZ_QUESTIONS),
        progress=((quiz_index + 1) / len(QUIZ_QUESTIONS)) * 100,
    )


@app.route("/quiz/answer", methods=["POST"])
@login_required
def quiz_answer():
    answer = request.form.get("answer", "").strip().lower()
    question_id = request.form.get("question_id", "").strip()
    if answer not in ["yes", "no"] or not question_id:
        flash("Please select a valid answer.", "error")
        return redirect(url_for("quiz"))

    answers = session.get("quiz_answers", {})
    answers[question_id] = answer
    session["quiz_answers"] = answers
    session["quiz_index"] = int(session.get("quiz_index", 0)) + 1

    if session["quiz_index"] >= len(QUIZ_QUESTIONS):
        return redirect(url_for("quiz_result"))
    return redirect(url_for("quiz"))


@app.route("/quiz/result")
@login_required
def quiz_result():
    answers = session.get("quiz_answers", {})
    existing_profile = get_user_profile(session["user_id"]) or {}
    top_careers, confidence_map = calculate_quiz_recommendations(answers)
    career_prediction = top_careers[0]["name"]
    confidence_score = confidence_map.get(career_prediction, top_careers[0]["score"])
    quiz_profile = build_quiz_profile(answers)
    marks_value = existing_profile.get("marks")
    education_value = existing_profile.get("education") or quiz_profile["education"]
    resources = get_career_resources(career_prediction)

    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO assessment_history
        (user_id, marks, stream, interest, skill, talent, education, predicted_career, confidence_score, top_careers_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            marks_value,
            "quiz-assessment",
            quiz_profile["interest"],
            quiz_profile["skill"],
            "quiz-derived",
            education_value,
            career_prediction,
            confidence_score,
            json.dumps(top_careers),
        ),
    )
    connection.commit()
    connection.close()

    session.pop("quiz_answers", None)
    session.pop("quiz_index", None)

    return render_template(
        "quiz_result.html",
        career=career_prediction,
        marks=marks_value,
        education=education_value,
        top_careers=top_careers,
        confidence_score=confidence_score,
        skills=resources["skills"],
        certifications=resources["certifications"],
        internships=resources["internships"],
        courses=resources["courses"],
        packages=resources["packages"],
        roadmap=resources["roadmap"],
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("register.html")
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        connection = get_db_connection()
        existing_user = connection.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email),
        ).fetchone()
        if existing_user:
            connection.close()
            flash("Username or email already exists.", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        connection.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        connection.commit()
        connection.close()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")

        if not username_or_email or not password:
            flash("Please enter your username/email and password.", "error")
            return render_template("login.html")

        connection = get_db_connection()
        user = connection.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username_or_email, username_or_email.lower()),
        ).fetchone()
        connection.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("home"))

        flash("Invalid credentials. Please try again.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    answer = None
    question = ""
    use_llm = bool(LLM_API_KEY)
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = llm_chatbot_answer(question) if use_llm else chatbot_answer(question)
    return render_template("chat.html", question=question, answer=answer, use_llm=use_llm)


@app.route("/predict", methods=["POST"])
@login_required
def predict():
    marks = request.form.get("marks", "0")
    stream = request.form.get("stream", "")
    interest = request.form.get("interest", "")
    skill = request.form.get("skill", "")
    talent = request.form.get("talent", "")
    education = request.form.get("education", "")

    if not all([stream, interest, skill, talent, education]):
        flash("Please fill all assessment fields before prediction.", "error")
        return redirect(url_for("home"))

    try:
        marks_value = float(marks)
    except ValueError:
        marks_value = 0.0

    (
        career_prediction,
        labels,
        probabilities,
        top_careers,
        confidence_score,
    ) = run_prediction(marks_value, stream, interest, skill, talent, education)

    govt_jobs = recommend_government_jobs(education)
    internships = recommend_internships(skill, interest)
    career_category = CAREER_CATEGORIES.get(career_prediction, "General")
    resources = get_career_resources(career_prediction)
    courses = resources["courses"]
    roadmap = resources["roadmap"]
    skill_paths = resources["skills"]
    certifications = resources["certifications"]
    packages = resources["packages"]
    ai_plan = generate_llm_career_plan(
        career_prediction,
        marks_value,
        stream,
        interest,
        skill,
        talent,
        education,
    ) if LLM_API_KEY else None

    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO assessment_history
        (user_id, marks, stream, interest, skill, talent, education, predicted_career, confidence_score, top_careers_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            marks_value,
            stream,
            interest,
            skill,
            talent,
            education,
            career_prediction,
            confidence_score,
            json.dumps(top_careers),
        ),
    )
    connection.commit()
    connection.close()

    return render_template(
        "result.html",
        career=career_prediction,
        top_careers=top_careers,
        confidence_score=confidence_score,
        career_category=career_category,
        career_labels=labels,
        career_probs=probabilities,
        govt_jobs=govt_jobs,
        internships=internships,
        skill_paths=skill_paths,
        certifications=certifications,
        packages=packages,
        courses=courses,
        roadmap=roadmap,
        marks=marks_value,
        stream=stream,
        interest=interest,
        skill=skill,
        talent=talent,
        education=education,
        ai_plan=ai_plan,
        use_llm=bool(LLM_API_KEY),
    )


init_db()


if __name__ == "__main__":
    app.run(debug=True)
