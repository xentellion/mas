import json
from llm_api.gigachat.gigachat_api import GigachatSession


def main():
    session = GigachatSession()
    response = session.request(
        "Ты профессиональный переводчик на английский язык. Переведи точно сообщение пользователя.",
        "GigaChat — это сервис, который умеет взаимодействовать с пользователем в формате диалога, писать код, создавать тексты и картинки по запросу пользователя.",
    )
    print(json.dumps(response, sort_keys=True, indent=4))


if __name__ == "__main__":
    main()
