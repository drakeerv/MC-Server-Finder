from dotenv import load_dotenv
from finder import run_scanner

load_dotenv()  # Loading .env first before doing anything else

if __name__ == "__main__":
    run_scanner()
