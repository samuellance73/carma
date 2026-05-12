from src.utils import format_transcript

messages = [
    {
        'id': '1',
        'author': 'Alice',
        'content': 'Hey carma, what is up?',
        'timestamp': '2023-10-27T10:00:00',
        'reply_to': None
    },
    {
        'id': '2',
        'author': 'Carma',
        'content': 'not much Alice, just chilling',
        'timestamp': '2023-10-27T10:01:00',
        'reply_to': '1'
    },
    {
        'id': '3',
        'author': 'Bob',
        'content': 'can someone help me with math?',
        'timestamp': '2023-10-27T10:02:00',
        'reply_to': None
    },
    {
        'id': '4',
        'author': 'Carma',
        'content': 'sure bob what is the problem',
        'timestamp': '2023-10-27T10:03:00',
        'reply_to': '3'
    }
]

print("--- Transcript ---")
print(format_transcript(messages))
