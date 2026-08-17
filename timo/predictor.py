# Recursos do assistente Timo: previsão de intenções.
# Dependências externas.
import joblib

# Módulos internos da aplicação.
from timo.model_storage import active_model_path

class IntentPredictor:
    # Inicializa as dependências e o estado da instância.
    def __init__(self):
        if not active_model_path().exists():
            raise RuntimeError(
                "Modelo do Timo não encontrado. "
                "Execute: python -m timo.trainer"
            )
        self.reload()

    def reload(self):
        self.model_path = active_model_path()
        self.model_mtime_ns = self.model_path.stat().st_mtime_ns
        self.model = joblib.load(self.model_path)

    def reload_if_changed(self):
        """Sincroniza workers que não executaram o treino diretamente."""
        model_path = active_model_path()
        model_mtime_ns = model_path.stat().st_mtime_ns
        if model_path != self.model_path or model_mtime_ns != self.model_mtime_ns:
            self.reload()

    def predict(self, text: str):
        self.reload_if_changed()
        probabilities = self.model.predict_proba([text])[0]

        index = probabilities.argmax()

        intent = self.model.classes_[index]
        confidence = float(probabilities[index])

        return { "intent": intent, "confidence": confidence }


predictor = IntentPredictor()
