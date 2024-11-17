import os
import asyncio
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from dotenv import load_dotenv, find_dotenv
from colorama import init
init(autoreset=True)

# ANSI escape codes for colors
RED = "\033[31m"
GREEN = "\033[32m"
TEXT_CYAN = "\033[36m"  # Cyan text
RESET = "\033[0m"  # Reset color to default

async def generate_session(api_id: int, api_hash: str):
    while True:
        try:
            # Use the TelegramClient with the StringSession
            async with TelegramClient(StringSession(), api_id, api_hash) as client:
                session = client.session.save()  # Save the session string
                return session  # Return the session string
        except Exception as e:
            print(f"{RED}Something went wrong: {e}{RESET}")
            continue  # Continue to retry if an error occurs

def save_session(session_string: str):
    # Create the sessions folder if it doesn't exist
    if not os.path.exists('sessions'):
        os.makedirs('sessions')

    while True:
        # Prompt the user for a session name
        session_name = input("Enter a name for the session: ")
        session_file_path = os.path.join('sessions', f"{session_name}.session")

        # Check if the session file already exists
        if os.path.exists(session_file_path):
            print(f"{RED}Error: A session file with the name{RESET} {TEXT_CYAN}'{session_name}.session'{RESET} {RED}already exists. Please choose a different name.{RESET}")
        else:
            # Save the session string to the file
            with open(session_file_path, 'w') as session_file:
                session_file.write(session_string)
            print(f"{GREEN}Session saved successfully as{RESET} {TEXT_CYAN}'{session_file_path}'.{RESET}")
            break  # Exit the loop once saved successfully

# Example usage
if __name__ == '__main__':
    # Load environment variables from .env file
    load_dotenv(find_dotenv())  # This will search for the .env file

    # Retrieve API_ID and API_HASH from environment variables
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')

    # Check if .env file exists and if the variables are set correctly
    if api_id is None or api_hash is None:
        print(f"{RED}Error: API_ID and API_HASH must be set in the .env file.{RESET}")
        exit(1)

    # Check if they are empty
    if api_id.strip() == "" or api_hash.strip() == "":
        print(f"{RED}Error: API_ID and API_HASH cannot be empty.{RESET}")
        exit(1)

    # Ensure api_id is an integer
    try:
        api_id = int(api_id)
    except ValueError:
        print(f"{RED}Error: API_ID must be an integer.{RESET}")
        exit(1)

    # Run the async function using asyncio to generate the session
    session_string = asyncio.run(generate_session(api_id, api_hash))

    # Save the session string with a unique name
    save_session(session_string)
