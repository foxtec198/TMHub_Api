from pathlib import Path
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "data" / "intents.csv"
MODEL_PATH = BASE_DIR / "models" / "intent_model.pkl"

def train():
    df = pd.read_csv(DATASET_PATH)

    df = df.dropna(subset=["text", "intent"])

    X = df["text"].astype(str)
    y = df["intent"].astype(str)

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                lowercase=True,
                strip_accents="unicode",
                min_df=1
            )
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced"
            )
        )
    ])

    model.fit(X, y)
    MODEL_PATH.parent.mkdir( parents=True, exist_ok=True )
    joblib.dump(model, MODEL_PATH)

    print("Modelo treinado.")
    print(f"Exemplos: {len(df)}")
    print(f"Intents: {df['intent'].nunique()}")
    print(f"Salvo em: {MODEL_PATH}")

if __name__ == "__main__": train()