import sys
import json
import requests
import openai
from utils import get_values
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QListWidget
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

# OpenAI Key
openai.api_key = "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"

with open("schema.txt", "r") as schema_file:
    schema_prompt = schema_file.read()

prime_query_prompt = "query top_n_associated_diseases {\n  search(queryString:"


class GeneticsGPTGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GeneticsGPT")
        self.setGeometry(100, 100, 800, 600)

        # main widget and layout
        central_widget = QWidget(self)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setCentralWidget(central_widget)

        # left section layout
        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        main_layout.addLayout(left_layout)

        # logo label
        logo_label = QLabel(self)
        logo_pixmap = QPixmap("logo.png")  # Replace with your logo image file
        logo_pixmap = logo_pixmap.scaledToWidth(
            200)  # Adjust the logo size as needed
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(logo_label)

        # question input field
        self.question_input_field = QLineEdit(self)
        self.question_input_field.setPlaceholderText("Ask a question...")
        self.question_input_field.setFont(QFont("Arial", 14))
        self.question_input_field.setStyleSheet(
            "padding: 10px; border-radius: 5px;")
        left_layout.addWidget(self.question_input_field)

        # submit button
        self.submit_button = QPushButton("Submit", self)
        self.submit_button.clicked.connect(self.handle_submit)
        self.submit_button.setFont(QFont("Arial", 14))
        self.submit_button.setStyleSheet(
            "padding: 10px; background-color: #4285F4; color: white; border-radius: 5px;")
        left_layout.addWidget(self.submit_button)

        # answer widget
        self.answer_widget = QTextEdit(self)
        self.answer_widget.setReadOnly(True)
        self.answer_widget.setFont(QFont("Arial", 12))
        self.answer_widget.setStyleSheet(
            "background-color: #f0f0f0; color: black; padding: 10px; border-radius: 5px;")
        left_layout.addWidget(QLabel("Answers:"))
        left_layout.addWidget(self.answer_widget)

        # FAQ list
        self.faq_list = QListWidget(self)
        self.faq_list.itemClicked.connect(self.handle_faq_click)
        left_layout.addWidget(QLabel("Frequently Asked Questions:"))
        left_layout.addWidget(self.faq_list)

        # answer text area
        self.answer_text_area = QTextEdit(self)
        self.answer_text_area.setReadOnly(True)
        self.answer_text_area.setFont(QFont("Arial", 12))
        self.answer_text_area.setStyleSheet(
            "background-color: #f0f0f0; color: black; padding: 10px; border-radius: 5px;")
        main_layout.addWidget(self.answer_text_area)

    def handle_submit(self):
        user_question = self.question_input_field.text()

        # prevent multiple requests
        self.submit_button.setEnabled(False)

        query_response = self.generate_query_response(user_question)

        self.answer_widget.setPlainText(query_response)

        # Generate FAQs based on the query response
        self.generate_faqs(query_response)

        self.submit_button.setEnabled(True)

    def handle_faq_click(self, item):
        faq_question = item.text()

        # Generate a response for the clicked FAQ
        self.generate_faq_response(faq_question)

    def generate_query_response(self, user_question):
        openai_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": schema_prompt},
                {"role": "user", "content": user_question},
                {"role": "system", "content": prime_query_prompt},
            ],
            temperature=0,
            max_tokens=250,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=["###"],
        )
        generated_query = openai_response["choices"][0].message["content"]

        graphql_query = prime_query_prompt + generated_query

        # Set base URL of GraphQL API endpoint
        api_url = "https://api.platform.opentargets.org/api/v4/graphql"

        # Perform POST request and check status code of response
        try:
            api_response = requests.post(
                api_url, json={"query": graphql_query})
            api_response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
            QMessageBox.critical(
                self, "Error", "An error occurred while fetching data from the API.")
            return None

        # Transform API response from JSON into Python dictionary
        api_data = json.loads(api_response.text)

        try:
            search_hits = api_data["data"]["search"]["hits"][0]
        except (KeyError, IndexError):
            QMessageBox.warning(
                self, "Warning", "No results found for the given query.")
            return None

        diseases = get_values(search_hits, "disease")
        answer_text = "\n".join(
            f"{i+1}. {disease['name']}" for i, disease in enumerate(diseases))

        return answer_text

    def generate_faqs(self, query_response):
        if query_response:
            faq_prompt = f"Based on the following information:\n\n{query_response}\n\nGenerate 3-5 relevant frequently asked questions (FAQs) related to the diseases and genes mentioned. Provide each FAQ as a question only, without the 'Q:' prefix or any additional context."

            openai_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": schema_prompt},
                    {"role": "user", "content": faq_prompt},
                ],
                temperature=0.7,
                max_tokens=200,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )

            generated_faqs = openai_response["choices"][0].message["content"]

            self.faq_list.clear()

            # Add generated FAQs to the list
            for faq in generated_faqs.split("\n"):
                self.faq_list.addItem(faq)

    def generate_faq_response(self, faq_question):
        faq_prompt = f"Q: {faq_question}\nA: Provide a concise and informative answer to the question, focusing on the key points and avoiding unnecessary details or technical jargon."

        openai_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": schema_prompt},
                {"role": "user", "content": faq_prompt},
            ],
            temperature=0.7,
            max_tokens=200,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )

        faq_response = openai_response["choices"][0].message["content"]
        self.answer_text_area.setPlainText(faq_response)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = GeneticsGPTGUI()
    gui.show()
    sys.exit(app.exec_())
