import base64
import email
import re
import streamlit as st
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


@st.cache_resource
def authenticate_gmail():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('gmail', 'v1', credentials=creds)
    return service


@st.cache_resource
def train_model():
    df = pd.read_csv("training_data.csv")
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(df["body"])
    y = df["category"]
    model = MultinomialNB()
    model.fit(X, y)
    return model, vectorizer


def summarize_text(text, sentence_count=2):
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text.split()) < 10:
        return text
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, sentence_count)
    return " ".join(str(sentence) for sentence in summary)


def classify_ml(model, vectorizer, text):
    text = re.sub(r'\s+', ' ', text).strip().lower()
    X_input = vectorizer.transform([text])
    return model.predict(X_input)[0]


def fetch_emails(service, model, vectorizer, max_results=5):
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    email_data = []

    for msg in messages:
        msg_id = msg['id']
        msg_detail = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
        msg_str = base64.urlsafe_b64decode(msg_detail['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_str)

        subject = mime_msg['subject']
        sender = mime_msg['from']
        body = ""

        for part in mime_msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break

        summary = summarize_text(body)
        category = classify_ml(model, vectorizer, body)

        email_data.append({
            'From': sender,
            'Subject': subject,
            'Summary': summary,
            'Category': category
        })

    return email_data


def main():
    st.title("📬 Gmail Analyzer Dashboard (ML Edition)")
    max_results = st.slider("📥 How many recent emails to fetch?", 1, 20, 5)

    if st.button("🔄 Fetch Emails"):
        with st.spinner("Authenticating & analyzing emails..."):
            service = authenticate_gmail()
            model, vectorizer = train_model()
            data = fetch_emails(service, model, vectorizer, max_results)
            df = pd.DataFrame(data)
            st.success(f"Fetched and analyzed {len(df)} emails!")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📁 Download CSV", data=csv, file_name="emails.csv", mime="text/csv")


if __name__ == "__main__":
    main()
