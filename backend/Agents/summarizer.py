import re
import time
from ollama import chat


class TechnicalTextSummarizer:
    def __init__(
        self,
        model="gpt-oss:20b-cloud",
        chunk_size=10000,
        max_workers=1,
        max_summary_words=1500,  # Renamed to reflect a hard ceiling rather than a target
        retry_attempts=3,
        retry_delay=5
    ):
        self.model = model
        self.chunk_size = chunk_size
        self.max_workers = max_workers
        self.max_summary_words = max_summary_words
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

    def ingest_text(self, text):
        if not isinstance(text, str):
            raise ValueError("Input must be a string")

        if not text.strip():
            raise ValueError("Input text is empty")

        return text

    def preprocess_text(self, text):
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\t+", " ", text)
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(.)\1{15,}", r"\1", text)
        return text.strip()

    def split_into_chunks(self, text):
        paragraphs = text.split("\n")
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            if len(paragraph) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                for i in range(0, len(paragraph), self.chunk_size):
                    chunks.append(paragraph[i:i + self.chunk_size])

                continue

            if len(current_chunk) + len(paragraph) < self.chunk_size:
                current_chunk += paragraph + "\n"
            else:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    # Updated to accept a dynamic system_prompt
    def call_model(self, prompt, system_prompt):
        for attempt in range(self.retry_attempts):
            try:
                response = chat(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                return response["message"]["content"]

            except Exception as error:
                if attempt == self.retry_attempts - 1:
                    raise error

                print(f"Retrying model call {attempt + 1}/{self.retry_attempts}")
                time.sleep(self.retry_delay)

    def summarize_chunk(self, chunk, chunk_number):
        # The Circuit Breaker: Prevent processing of meaningless chunks
        if len(chunk.split()) < 20:
            return f"Insufficient context for technical summarization.\n\nContent:\n{chunk}"

        system_prompt = (
            "You are a strict technical summarizer.\n\n"
            "Rules:\n"
            "1. ONLY summarize information explicitly present in the provided text.\n"
            "2. Never invent facts or extrapolate data.\n"
            "3. Never infer missing architecture.\n"
            "4. If insufficient information exists, state that clearly.\n"
            "5. If the chunk contains only a keyword or short phrase, explain that there is not enough context to produce a technical summary."
        )

        prompt = (
            f"This is chunk {chunk_number} from a dataset.\n\n"
            f"Extract explicitly stated technical insights, analytical findings, relationships, and important details.\n"
            f"Create a structured summary preserving factual information without adding outside knowledge.\n\n"
            f"Text to analyze:\n"
            f"{chunk}"
        )

        return self.call_model(prompt, system_prompt)

    def summarize_all_chunks(self, chunks):
        summaries = []

        for index, chunk in enumerate(chunks):
            print(f"Processing chunk {index + 1} of {len(chunks)}")
            summary = self.summarize_chunk(chunk, index + 1)
            summaries.append(summary)

        return "\n\n".join(summaries)

    def create_final_summary(self, combined_summary):
        system_prompt = (
            "You are a technical synthesis engine. Your sole purpose is to aggregate text intelligently without hallucinating."
        )

        prompt = (
            f"Merge the following summaries into a single cohesive document.\n\n"
            f"Rules for synthesis:\n"
            f"- Do not introduce any new information.\n"
            f"- Only include information explicitly stated in the summaries below.\n"
            f"- If the combined summaries lack sufficient detail, state that additional context is required.\n"
            f"- Do not fabricate explanations or assumptions.\n\n"
            f"Maximum length: {self.max_summary_words} words.\n\n"
            f"Summaries to merge:\n"
            f"{combined_summary}"
        )

        return self.call_model(prompt, system_prompt)

    def summarize(self, raw_text):
        print("Validating input")
        text = self.ingest_text(raw_text)

        print("Preprocessing text")
        cleaned_text = self.preprocess_text(text)

        print("Splitting into chunks")
        chunks = self.split_into_chunks(cleaned_text)

        print(f"Total chunks created: {len(chunks)}")

        print("Starting chunk analysis")
        chunk_summaries = self.summarize_all_chunks(chunks)

        print("Generating final summary")
        final_summary = self.create_final_summary(chunk_summaries)

        return final_summary