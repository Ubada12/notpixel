import os
import re
import subprocess
from colorama import init
init(autoreset=True)

# ANSI escape codes for colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
TEXT_CYAN = "\033[36m"  # Cyan text
CYAN = "\033[46m"
BLUE = "\033[44m"
RESET = "\033[0m"  # Reset color to default

def display_menu():
    print(f"{YELLOW}Choose an option:{RESET}")
    print(f"{YELLOW}1. Run Bot{RESET}")
    print(f"{YELLOW}2. Create session{RESET}")
    print(f"{YELLOW}0. Exit{RESET}")

def run_bot():
    # Run another Python script using subprocess
    try:
        subprocess.run([sys.executable, "notpixel.py"], check=True)
    except FileNotFoundError:
        print(f"{RED}Error: The file{RESET} {TEXT_CYAN}'notpixel.py'{RESET} {RED}was not found.{RESET}")
    except KeyboardInterrupt:
        print(f"{RED}Process interrupted by user.{RESET}")
    except Exception as e:
        print(f"{RED}An error occurred: {e}{RESET}")

def create_session():
    # Run another Python script using subprocess
    print("Creating session...")
    try:
        subprocess.run([sys.executable, "generate_session_strg.py"], check=True)
    except FileNotFoundError:
        print(f"{RED}Error: The file{RESET} {TEXT_CYAN}'generate_session_strg.py'{RESET} {RED}was not found.{RESET}")
    except Exception as e:
        print(f"{RED}An error occurred: {e}{RESET}")

def main():
    while True:
        display_menu()
        try:
            choice = input("Enter your choice: ").strip()
            
            if choice == "1":
                # Check if the sessions folder exists
                if not os.path.exists('sessions'):
                    print(f"{RED}Error:{RESET} {TEXT_CYAN}'sessions'{RESET} {RED}folder not found. Please create it before proceeding.{RESET}")
                    continue  # Go back to the menu
                run_bot()
            elif choice == "2":
                create_session()
            elif choice == "0":
                print(f"{RED}Exiting...{RESET}")
                break
            else:
                print(f"{RED}Invalid choice, please select again.{RESET}")
        except EOFError:
            print()
            print(f"{RED}No input received. Exiting the program.{RESET}")
            break  # Exit the loop if no input is received
        except KeyboardInterrupt:
            print()
            print(f"{RED}Process interrupted by user.{RESET}")
            break

if __name__ == "__main__":
    main()
