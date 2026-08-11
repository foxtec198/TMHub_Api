from pathlib import Path
import joblib

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "intent_model.pkl"

class IntentPredictor:
    def __init__(self):
        if not MODEL_PATH.exists():
            raise RuntimeError(
                "Modelo do Timo não encontrado. "
                "Execute: python -m timo.trainer"
            )
        self.reload()

    def reload(self):
        self.model = joblib.load(MODEL_PATH)

    def predict(self, text: str):
        probabilities = self.model.predict_proba([text])[0]

        index = probabilities.argmax()

        intent = self.model.classes_[index]
        confidence = float(probabilities[index])

        return { "intent": intent, "confidence": confidence }


predictor = IntentPredictor()
