import joblib

from timo.model_storage import active_model_path

class IntentPredictor:
    def __init__(self):
        if not active_model_path().exists():
            raise RuntimeError(
                "Modelo do Timo não encontrado. "
                "Execute: python -m timo.trainer"
            )
        self.reload()

    def reload(self):
        self.model = joblib.load(active_model_path())

    def predict(self, text: str):
        probabilities = self.model.predict_proba([text])[0]

        index = probabilities.argmax()

        intent = self.model.classes_[index]
        confidence = float(probabilities[index])

        return { "intent": intent, "confidence": confidence }


predictor = IntentPredictor()
