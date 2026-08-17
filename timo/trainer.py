# Recursos do assistente Timo: treinamento do modelo.
# Biblioteca padrão.
from pathlib import Path
# Dependências externas.
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Módulos internos da aplicação.
from timo.analytics_catalog import ANALYTICS_TRAINING_EXAMPLES
from timo.model_storage import ensure_trained_model_directory
from timo.navigation_catalog import NAVIGATION_TRAINING_EXAMPLES

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "data" / "intents.csv"

def train(extra_examples=None):
    df = pd.read_csv(DATASET_PATH)
    generated_examples = pd.DataFrame([
        *NAVIGATION_TRAINING_EXAMPLES,
        *ANALYTICS_TRAINING_EXAMPLES,
    ])
    frames = [df, generated_examples]
    if extra_examples:
        frames.append(pd.DataFrame(extra_examples))
    df = pd.concat(frames, ignore_index=True)

    df = df.dropna(subset=["text", "intent"])
    df = df.drop_duplicates(subset=["text", "intent"])

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
    model_path = ensure_trained_model_directory()
    joblib.dump(model, model_path)

    print("Modelo treinado.")
    print(f"Exemplos: {len(df)}")
    print(f"Intents: {df['intent'].nunique()}")
    print(f"Salvo em: {model_path}")
    return model_path

if __name__ == "__main__": train()
