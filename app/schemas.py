from fastapi import Form

class ChatForm:
    def __init__(self, question: str = Form(...)):
        self.question = question

