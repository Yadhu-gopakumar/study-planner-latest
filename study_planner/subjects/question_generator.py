# question_generator.py
import re
import joblib
import pdfplumber
import numpy as np
import nltk
from nltk.tokenize import sent_tokenize


import os

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "q_gen_model.pkl")

# Load trained TF-IDF model using the absolute path
vectorizer = joblib.load(model_path)
# Download tokenizer (safe even if already present)
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")


# -------------------- PDF TEXT EXTRACTION --------------------
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
    return text


# -------------------- TEXT CLEANING --------------------
def clean_text(text):
    # remove bullets and symbols
    text = re.sub(r"[•●▪■►–—]", " ", text)

    # remove extra spaces and newlines
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# -------------------- SENTENCE FILTER --------------------
def is_valid_sentence(sentence):
    bad_keywords = [
        "was developed by",
        "has since become",
        "early 1990s",
        "operational description",
        "the actual operation",
        "offers the service of",
        "sender generates",
        "receiver uses",
        "most electronic mail systems",
        "permit only",
        "example", "for example", "e.g", "i.e",
        "note", "important when", "in other words"
    ]

    s = sentence.lower()

    if any(bad in s for bad in bad_keywords):
        return False

    if len(sentence.split()) < 6:
        return False

    return True



def concept_key(question):
    return question.lower().split()[:3]


# -------------------- SENTENCE RANKING --------------------
# def rank_sentences(sentences):
#     tfidf_matrix = vectorizer.transform(sentences)
#     sentence_scores = tfidf_matrix.sum(axis=1).A1
#     ranked_indexes = rank_sentences([clean_text(s) for s in sentences])
#     return ranked_indexes

def rank_sentences(sentences):
    # Clean the sentences first if you want, then transform
    cleaned_sentences = [clean_text(s) for s in sentences]
    tfidf_matrix = vectorizer.transform(cleaned_sentences)
    
    # Calculate scores
    sentence_scores = tfidf_matrix.sum(axis=1).A1
    ranked_indexes = np.argsort(sentence_scores)[::-1]
    
    return ranked_indexes

# -------------------- QUESTION GENERATION --------------------
# def make_question(sentence):
#     s = sentence.lower()

#     if "email security" in s and "enhancement" in s:
#         return "Explain the primary goal of email security"

#     if "confidentiality" in s or "authentication" in s or "integrity" in s:
#         return "Explain confidentiality, authentication, and integrity in email security"

#     if "audit" in s and "reporting" in s:
#         return "Explain audit and reporting in email security"

#     if "scheme" in s and "pgp" in s:
#         return "Explain the scheme used in PGP"

#     if "operation" in s and "pgp" in s:
#         return "Explain the operation of PGP"

#     if "session key" in s:
#         return "Explain session key decryption in PGP"

#     if "ascii" in s or "radix" in s:
#         return "Explain ASCII conversion in PGP"

#     if "key ring" in s:
#         return "Explain private key ring and public key ring"

#     if "primary goal" in s:
#         return "Explain the primary goal of email security"
   
#     return "Explain: " + sentence.capitalize()
def make_question(sentence):
    s = sentence.lower()

    if s.startswith(("what is", "define", "explain")):
        return sentence.strip("?") + "?"

    if " is " in s:
        return "What is " + sentence.split(" is ")[0].strip().capitalize() + "?"

    if " are " in s:
        return "What are " + sentence.split(" are ")[0].strip().capitalize() + "?"

    if " used for " in s or " used to " in s:
        return "Explain the use of " + sentence.split(" used")[0].strip().capitalize()

    if " consists of " in s or " includes " in s:
        return "Explain the components of " + sentence.split(" ")[0].capitalize()

    if " process " in s or " operation " in s:
        return "Explain the process described"

    return "Explain: " + sentence.capitalize()

#    return None




def normalize_sentence(sentence):
    sentence = re.sub(r"[•●▪■]", "", sentence)
    sentence = re.sub(r"\d+\.", "", sentence)

    # remove long explanations after colon
    sentence = sentence.split(":")[0]

    # remove repeated words
    words = sentence.split()
    unique_words = []
    for w in words:
        if w.lower() not in [uw.lower() for uw in unique_words]:
            unique_words.append(w)

    sentence = " ".join(unique_words)

    # limit length
    if len(sentence.split()) > 12:
        sentence = " ".join(sentence.split()[:12])

    return sentence.strip()

def expand_question(question):
    expansions = []

    if "email security" in question.lower():
        expansions.append("Explain threats addressed by email security")
        expansions.append("Explain the need for email security")

    if "pgp" in question.lower():
        expansions.append("Explain services provided by PGP")
        expansions.append("Explain confidentiality service in PGP")

    if "confidentiality" in question.lower():
        expansions.append("Differentiate confidentiality and integrity")

    if "key ring" in question.lower():
        expansions.append("Differentiate private key ring and public key ring")

    if "session key" in question.lower():
        expansions.append("Explain session key generation in PGP")

    return expansions


# -------------------- MAIN PIPELINE --------------------
def generate_questions_from_pdf(pdf_path, limit=10):

    text = extract_text_from_pdf(pdf_path)
    text = clean_text(text)
    # print("Extracted text length:", len(text))
    sentences = sent_tokenize(text)


    sentences = [s for s in sentences if is_valid_sentence(s)]

    if not sentences:
        return []

    ranked_indexes = rank_sentences(sentences)

    questions = []
    seen_questions = set()
    seen_concepts = set()

    # ---------- PHASE 1: CORE QUESTIONS ----------
    for i in ranked_indexes:
        sentence = normalize_sentence(sentences[i])
        q = make_question(sentence)

        if q is None:
            continue

        if not (5 < len(q.split()) < 30):
            continue

        q_key = q.lower()
        if q_key in seen_questions:
            continue

        concept_sig = " ".join(q.lower().split()[:3])
        if concept_sig in seen_concepts:
            continue

        

        seen_questions.add(q_key)
        seen_concepts.add(concept_sig)
        questions.append(q)

        if len(questions) >= limit:
            return questions

    # ---------- PHASE 2: EXPANSION ----------
    if len(questions) < limit:
        expanded = []
        for q in questions:
            expanded.extend(expand_question(q))

        for q in expanded:
            q_key = q.lower()
            if q_key not in seen_questions:
                questions.append(q)
                seen_questions.add(q_key)

            if len(questions) >= limit:
                break

    return questions

def generate_questions_from_text(text, limit=10):
    text = clean_text(text)
    sentences = sent_tokenize(text)

    sentences = [s for s in sentences if is_valid_sentence(s)]
    if not sentences:
        return []

    ranked_indexes = rank_sentences(sentences)

    questions = []
    seen = set()

    for i in ranked_indexes:
        sentence = normalize_sentence(sentences[i])
        q = make_question(sentence)

        if q and q.lower() not in seen:
            questions.append(q)
            seen.add(q.lower())

        if len(questions) >= limit:
            break

    return questions
