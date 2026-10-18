import requests

from backend.app.core.config import settings


class OllamaService:

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    def is_available(self) -> bool:
        """
        Check whether Ollama is running.
        """

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )

            return response.status_code == 200

        except requests.RequestException:
            return False

    def get_models(self):
        """
        Return models installed in Ollama.
        """

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )

            response.raise_for_status()

            data = response.json()

            return [
                model["name"]
                for model in data.get("models", [])
            ]

        except requests.RequestException:
            return []

    def chat(self, message: str) -> str:
        """
        Send a message to the local Ollama model.
        """

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ],
            "stream": False,
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            )

            response.raise_for_status()

            data = response.json()

            return data["message"]["content"]

        except requests.RequestException as error:
            raise RuntimeError(
                f"Could not connect to Ollama: {error}"
            )

        except KeyError:
            raise RuntimeError(
                "Ollama returned an unexpected response."
            )


ollama_service = OllamaService()