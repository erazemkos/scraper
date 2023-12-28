from abc import ABC, abstractmethod
import os
import re


def summarizer_factory(summarizer):
    if summarizer == "sloT5":
        return SloT5Summarizer()
    if summarizer == "chatgpt":
        return ChatGPTSummarizer()


class BaseSummarizer(ABC):
    @abstractmethod
    def get_headline_and_summary(self, text: str) -> tuple[str, str]:
        ...


class SloT5Summarizer(BaseSummarizer):
    HEADLINE_MODEL_PATH = 'model/SloT5-sta_headline'
    SUMMARY_MODEL_PATH = 'model/SloT5-cnndm_slo_pretraining'
    from transformers import T5Tokenizer, T5ForConditionalGeneration

    def __init__(self):
        self.headline_tokenizer = self.T5Tokenizer.from_pretrained(self.HEADLINE_MODEL_PATH)
        self.headline_model = self.T5ForConditionalGeneration.from_pretrained(self.HEADLINE_MODEL_PATH)

        self.summary_tokenizer = self.T5Tokenizer.from_pretrained(self.SUMMARY_MODEL_PATH)
        self.summary_model = self.T5ForConditionalGeneration.from_pretrained(self.SUMMARY_MODEL_PATH)

    def get_headline_and_summary(self, text: str) -> tuple[str, str]:
        headline = self._clean_string(self._get_inference(text, self.headline_model, self.headline_tokenizer))
        summary = self._clean_string(self._get_inference(text, self.summary_model, self.summary_tokenizer))
        return headline, summary

    @staticmethod
    def _get_inference(text: str, model: T5ForConditionalGeneration, tokenizer: T5Tokenizer):
        input_ids = tokenizer(f"summarize: {text}", return_tensors="pt", max_length=512, truncation=True).input_ids
        input_ids = input_ids.to('cpu')
        outputs = model.generate(input_ids,
                                 max_length=256,
                                 num_beams=5,
                                 no_repeat_ngram_size=5
                                 )
        return tokenizer.decode(outputs[0], skip_special_tokens=True)

    @staticmethod
    def _clean_string(text):
        return text.replace("(dopolnjeno)", "")


class ChatGPTSummarizer(BaseSummarizer):
    """ Uses openai api to generate slovenian headline and summary. """

    import openai as _openai
    import tiktoken as _tiktoken

    def __init__(self, chat_model="gpt-3.5-turbo-16k", model_token_limit=8192, max_tokens=4000):
        self._openai.api_key = os.getenv("OPENAI_API_KEY")
        self._chat_model = chat_model
        self._model_token_limit = model_token_limit
        self._max_tokens = max_tokens
        # Initialize the tokenizer
        self.tokenizer = self._tiktoken.encoding_for_model(chat_model)

    def get_headline_and_summary(self, text: str) -> tuple[str, str]:
        response = self._send_to_openai_model(text)
        return self._split_first_sentence(response.replace("\n-", "").replace("\n", "").strip())

    def _send_to_openai_model(self, text):
        if not text:
            return "Error: Text data is missing. Please provide a prompt."
        base_prompt = {
                "role": "user",
                "content": "I will send you an article in slovenian language. Your answer should have "
                           "the following structure: The first sentence of your answer "
                           "should be a short headline in slovenian language in a maximum of 12 words. After that "
                           "sentence you should write a short summary of the article in a maximum of 3 sentences in"
                           " slovenian language. "
                           "Your answer should focus on the important information and do not include anything else in "
                           "your answer but these 4 sentences and everything should be in slovenian language. No "
                           "newlines separating the sentences. Only sentences ending with dots. This is "
                           f"the article: {text}"
            }
        response = self._openai.ChatCompletion.create(model=self._chat_model, messages=[base_prompt])
        final_response = response.choices[0].message["content"].strip()
        return final_response

    def _prepare_chunks(self, text):
        token_integers = self.tokenizer.encode(text)

        # Split the token integers into chunks based on max_tokens
        chunk_size = self._max_tokens - len(self.tokenizer.encode(text))
        chunks = [
            token_integers[i: i + chunk_size]
            for i in range(0, len(token_integers), chunk_size)
        ]

        # Decode token chunks back to strings
        return [self.tokenizer.decode(chunk) for chunk in chunks]

    @staticmethod
    def _split_first_sentence(text: str) -> tuple[str, str]:
        # Use regular expression to split sentences considering possible dates with dots.
        sentences = re.split(r'(?<!\d)(?<!\d\.\d)(?<!\d\.\d\.\d)\.\s', text)
        # Add the dot back at the end of each sentence.
        sentences = [sentence.strip() + '.' if sentence.strip()[-1] != '.' else sentence.strip() for sentence in
                     sentences
                     if sentence]
        first_sentence = sentences[0]
        rest_of_text = ' '.join(sentences[1:])
        return first_sentence, rest_of_text
