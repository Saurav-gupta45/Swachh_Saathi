import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# load dataset
df = pd.read_csv("/Users/sauravgupta/Desktop/project 1/src/civic_project/civic_issues.csv")

X = df["text"]
y = df["label"]

# train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ML pipeline
model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1,2), max_features=5000)),
    ("clf", LogisticRegression(max_iter=1000))
])

# train model
model.fit(X_train, y_train)

# authority mapping
authority_map = {
    "waste": "MCD",
    "water": "Delhi Jal Board",
    "air": "DPCC / CPCB",
    "transport": "Delhi Traffic Police / DTC",
    "energy": "BSES / Tata Power",
    "sanitation": "MCD Sanitation",
    "noise": "Delhi Police"
}

# function used by Flask
def civic_assistant(text):
    category = model.predict([text])[0]
    authority = authority_map.get(category, "General Helpline 311")
    return category, authority