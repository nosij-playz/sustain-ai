from backend.Agents.Master import WasteDispoMaster
from backend.output.tts_and_sst import speak, listen
import os
import time


class WasteDispoApp:
    """Unified application for waste disposal management with chat and speech interfaces."""

    def __init__(self, default_location=None):
        """Initialize the application with master agent and configuration."""
        self.default_location = default_location
        self.system_name = os.getenv("SUSTAINAI_SYSTEM_NAME", "SustainAi")
        self.master_name = os.getenv("SUSTAINAI_MASTER_NAME", "Lily")
        self.master = WasteDispoMaster(default_location=default_location)

    def is_status_query(self, text):
        """Check if the input is a status query."""
        keywords = ["status", "processing", "working", "update"]
        return any(word in text.lower() for word in keywords)

    def is_exit_query(self, text):
        """Check if the input is an exit command."""
        keywords = ["stop", "exit", "bye", "goodbye", "good bye", "shutdown", "quit", "close"]
        return any(word in text.lower() for word in keywords)

    def process_response(self, user_input, use_speech=False):
        """
        Process user input and return response.
        
        Args:
            user_input: The user's input text
            use_speech: If True, use text-to-speech for response
        
        Returns:
            The response from the master agent
        """
        if self.is_status_query(user_input):
            response = self.master.get_status_update()
            print(f"\n{self.master_name} (Status): {response}")
        else:
            response = self.master.process_input(user_input)
            print(f"\n{self.master_name}: {response}")

        if use_speech:
            speak(response)

        return response

    def start_chat_mode(self, analyze_images=False, image_list=None):
        """
        Start text-based chat interface.
        
        Args:
            analyze_images: If True, analyze images at startup
            image_list: List of image filenames to analyze
        """
        print(f"🚀 Starting {self.system_name} Command Center...")

        if analyze_images and image_list:
            upload_summaries = self.master._analyze_image_list(image_list)
            if upload_summaries:
                print(f"\n{self.master_name} (Image Analysis):")
                for summary in upload_summaries:
                    print(f"- {summary}")

        print(
            f"{self.master_name} is Online. "
            "You can initiate autonomous environmental analysis, request live ecosystem intelligence, "
            "trigger research workflows, or generate a fully interactive decision-support dashboard."
        )

        try:
            while True:
                user_in = input("\nYou: ")
                
                if self.is_exit_query(user_in):
                    break

                self.process_response(user_in, use_speech=False)

        finally:
            print("\n🧹 Cleaning session...")
            self.master.cleanup()
            print("Shutdown complete.")

    def start_speech_mode(self):
        """Start voice-based interface with speech recognition and text-to-speech."""
        print(f"🚀 Starting {self.system_name} Command Center...")

        welcome_message = (
            f"hello {self.master_name} is online. "
            "You can initiate autonomous environmental analysis, "
            "request live ecosystem intelligence, "
            "trigger research workflows, "
            "or generate a fully interactive decision support dashboard."
        )

        print(f"\n{self.master_name}: {welcome_message}")
        speak(welcome_message)

        try:
            while True:
                print("\n🎤 Listening...")
                user_in = listen()

                if not user_in:
                    time.sleep(0.5)  # Prevent rapid retries
                    continue

                print(f"\nYou (Voice): {user_in}")

                if self.is_exit_query(user_in):
                    goodbye = f"Alright. {self.master_name} signing off. Goodbye."
                    print(f"\n{self.master_name}: {goodbye}")
                    speak(goodbye)
                    break

                print(f"\n🧠 {self.master_name} processing...")
                self.process_response(user_in, use_speech=True)

        finally:
            print("\n🧹 Cleaning session...")
            self.master.cleanup()
            print("Shutdown complete.")

    def start_interactive_mode(self):
        """Start interactive mode where user can choose between chat and speech."""
        print(f"🚀 Starting {self.system_name} Command Center...\n")
        print(f"Welcome to {self.system_name}!")
        print("Choose your interface:")
        print("1. Chat Mode (Text-based)")
        print("2. Speech Mode (Voice-based)")

        choice = input("\nEnter your choice (1 or 2): ").strip()

        if choice == "1":
            self.start_chat_mode()
        elif choice == "2":
            self.start_speech_mode()
        else:
            print("Invalid choice. Starting chat mode by default.")
            self.start_chat_mode()


def main():
    """Main entry point for the application."""
    default_location = None
    
    app = WasteDispoApp(default_location=default_location)
    
    # Start interactive mode to let user choose interface
    app.start_interactive_mode()


if __name__ == "__main__":
    main()