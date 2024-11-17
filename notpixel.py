import os
import re
import sys
import sqlite3
import asyncio
import signal
import random
import requests
import httpx
from urllib.parse import unquote
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.types import InputBotAppShortName
from telethon.sessions import StringSession
from telethon import functions
from dotenv import load_dotenv, find_dotenv
from better_proxy import Proxy
from colorama import init
init(autoreset=True)

# Global variables
api_id = None
api_hash = None

# ANSI escape codes for colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
TEXT_CYAN = "\033[36m"  # Cyan text
CYAN = "\033[46m"
BLUE = "\033[44m"
RESET = "\033[0m"  # Reset color to default

# Graceful exit on Ctrl+C
def signal_handler(signal, frame):
    print(f"{RED}Exiting gracefully...{RESET}")
    asyncio.get_event_loop().stop()

# Register the signal handler for Ctrl+C (SIGINT)
signal.signal(signal.SIGINT, signal_handler)

# Connect to the database
def get_db_connection():
    conn = sqlite3.connect('queries.db')
    conn.row_factory = sqlite3.Row  # To return rows as dictionaries
    return conn

# Connect to the database
def get_db_connection_for_userINFO():
    conn = sqlite3.connect('user_info.db')
    conn.row_factory = sqlite3.Row  # To return rows as dictionaries
    return conn

# Create the queries table if it doesn't exist
def init_db():
    with get_db_connection() as db:
        db.execute('DROP TABLE IF EXISTS queries')  # Drop the table if it exists
        db.execute('''CREATE TABLE IF NOT EXISTS queries (
            proxy TEXT,
            session TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            bot_username TEXT NOT NULL,
            query TEXT NOT NULL UNIQUE
        )''')

# Create the queries table if it doesn't exist
def init_db4():
    with get_db_connection_for_userINFO() as db4:
        db4.execute('DROP TABLE IF EXISTS user_info')  # Drop the table if it exists
        db4.execute('''CREATE TABLE IF NOT EXISTS user_info (
            session_string TEXT NOT NULL PRIMARY KEY,
            proxy TEXT
        )''')

# Clear the queries table
def clear_queries():
    with get_db_connection() as db:
        db.execute('DELETE FROM queries')
        db.commit()

# Insert a new query into the database
def insert_query(proxy: str, session: str, user_id: int, name: str, bot_username: str, query: str):
    with get_db_connection() as db:
        db.execute('INSERT INTO queries (proxy, session, user_id, name, bot_username, query) VALUES (?, ?, ?, ?, ?, ?)',
                   (proxy, session, user_id, name, bot_username, query))
        db.commit()  # Save changes

# Insert a new query into the database
def insert_user_info(proxy: str, sessions: str):
    with get_db_connection_for_userINFO() as db4:
        db4.execute('INSERT INTO user_info (session_string, proxy) VALUES (?, ?)',
                   (sessions, proxy))
        db4.commit()  # Save changes

def validate_proxy(proxy_str: str) -> bool:
    try:
        # Parse the proxy using better_proxy
        proxy = Proxy.from_str(proxy_str)
        
        # Set up the requests proxy dictionary
        proxy_dict = {
            "http": f"{proxy.protocol}://{proxy.login}:{proxy.password}@{proxy.host}:{proxy.port}",
            "https": f"{proxy.protocol}://{proxy.login}:{proxy.password}@{proxy.host}:{proxy.port}"
        }
        
        # Test a request through the proxy
        response = requests.get("https://httpbin.org/ip", proxies=proxy_dict, timeout=10)
        
        # Check if we got a successful response
        if response.status_code == 200:
            ip_info = response.json()  # Get the IP information from the response
            print(f"{GREEN}Proxy is working!{RESET}")
            print(f"{YELLOW}IP address used:{RESET} {GREEN}{ip_info['origin']}{RESET}")
            return True
        else:
            print(f"{RED}Proxy failed with status code:{response.status_code}{RESET}")
            return False

    except requests.exceptions.ProxyError as pe:
        print(f"{RED}Proxy connection error: {pe}{RESET}")
        return False
    except requests.exceptions.Timeout:
        print(f"{RED}Request timed out while trying to connect through the proxy.{RESET}")
        return False
    except Exception as e:
        print(f"{RED}Proxy validation failed: {e}{RESET}")
        return False

# Function to generate query ID for a single session string
async def generate_query(session: str, bot_username: str, proxy=None):
    global api_id, api_hash  # Access the global variables

    if proxy is not None and not validate_proxy(proxy):
       print(f"{RED}Proxy is dead {proxy}{RESET}")
       exit(1)

    # Check and parse the proxy if provided
    if proxy:
        proxy = Proxy.from_str(proxy)  # Parse the proxy string
        proxy_string = str(proxy)
        proxy_dict = dict(
            proxy_type=proxy.protocol,
            addr=proxy.host,
            port=proxy.port,
            username=proxy.login,
            password=proxy.password
        )
    else:
        proxy_dict= None
        proxy_string = None

    # Create a TelegramClient with proxy settings
    if proxy_dict:
       client = TelegramClient(StringSession(session), api_id, api_hash, proxy=proxy_dict)
    else:
       client = TelegramClient(StringSession(session), api_id, api_hash)
       print(f"{YELLOW}No proxy is being used{RESET}")

    try:
        await client.connect()
        me = await client.get_me()
        if me is None:
           raise ValueError("Unable to fetch user details. Check session or network.")
        name = me.first_name + " " + (me.last_name if me.last_name else "")
        user_id = me.id

        # Request the web app view
        webapp_response = await client(functions.messages.RequestAppWebViewRequest(
            peer=bot_username,
            app=InputBotAppShortName(bot_id=await client.get_input_entity(bot_username), short_name="app"),
            platform="ios",
            write_allowed=True,
            start_param="6094625904"
        ))

        # Parse query data from the URL
        query = unquote(webapp_response.url.split("tgWebAppData=")[1].split("&")[0])
        print(f"{GREEN}Successfully Query ID generated for user{RESET} {TEXT_CYAN}{name}{RESET} {GREEN}| Bot:{RESET} {TEXT_CYAN}{bot_username}{RESET} {GREEN} | username:{RESET} {TEXT_CYAN}{me.username}{RESET}")
        print()
        insert_query(proxy_string, session, user_id, name, bot_username, query)  # Insert the query into the database

        await client.disconnect()

    except FloodWaitError as e:
        wait_time = e.seconds + random.uniform(10, 30)  # Add a small random jitter to avoid precise retry timings
        print(f"{RED}Rate limit encountered. Waiting for {e.seconds} seconds...{RESET}")
        await asyncio.sleep(wait_time)  # Wait for the required time
        return await generate_query(session, bot_username, proxy_string)  # Retry after waiting

    except Exception as e:
        await client.disconnect()
        print(f"{RED}Error while generating query: {e}{RESET}")
        exit(1)

# Function to load session strings from the 'sessions' folder and generate queries
async def generate_queries_for_all_sessions():
    with get_db_connection_for_userINFO() as db4:
        queries = db4.execute('SELECT * FROM user_info').fetchall()
        if not queries:
            print(f"{RED}No sessions found in database{RESET}")
            exit(1)
        else:
            for index, row in enumerate(queries):
                session_string = row[0]  # First element in the tuple
                proxy = row[1]           # Second element in the tuple
                await generate_query(session_string, "notpixel", proxy)
        
                # Check if it's the last iteration
                if index == len(queries) - 1:
                    print(f"{YELLOW}Successfully all sessions query IDs are inserted into the database.{RESET}")

def load_proxies(file_path):
    # Validate the existence of the file
    if not os.path.exists(file_path):
        print(f"{RED}Error: The file '{file_path}' does not exist.{RESET}")
        exit(1)

    # Read the file and store proxies in a list
    with open(file_path, 'r') as file:
        proxies = [line.strip() for line in file if line.strip()]  # Strip whitespace and filter out empty lines

    # Check if the file is empty
    if not proxies:
        print(f"{RED}Warning: The file '{file_path}' is empty.{RESET}")
    
    return proxies

def get_account_session_string_with_proxy():
    session_folder = 'sessions'

    proxies = load_proxies("proxies.txt")
    num_proxies = len(proxies)

    if not os.path.exists(session_folder):
        print(f"{RED}Error: '{session_folder}' folder not found.{RESET}")
        return

    for i, session_file in enumerate(os.listdir(session_folder)):
        if session_file.endswith('.session'):
            session_path = os.path.join(session_folder, session_file)
            print(f"{YELLOW}Processing session file:{RESET} {GREEN}{session_file}{RESET}")

            with open(session_path, 'r') as file:
                session_string = file.read().strip()

                # Use the proxy based on the index of the current session
                if i < num_proxies:
                    proxy = proxies[i]  # Use the corresponding proxy
                else:
                    proxy = None  # No more proxies available

                insert_user_info(proxy, session_string)

            # Check if this is the last iteration
            if i == len(os.listdir(session_folder)) - 1:
                print(f"{YELLOW}All accounts have been updated in the database.{RESET}")

async def get_balance(query, acc_name, k: int):
    url = "https://notpx.app/api/v1/mining/status"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "authorization": f"initData {query}",
        "origin": "https://app.notpx.app",
        "referer": "https://app.notpx.app/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                # Parse the JSON response
                data = response.json()
                user_balance = data.get("userBalance")
                charges = data.get("charges")
                max_charges = data.get("maxCharges")
                
                if k == 1:
                    print(f"{BLUE}{acc_name}{RESET} {YELLOW}--> Current Balance:{RESET} {GREEN}{user_balance}{RESET} {YELLOW}| Total Charges:{RESET} {GREEN}{charges}/{max_charges}{RESET}")
                elif k == 2:
                    print(f"{CYAN}{acc_name}{RESET} {YELLOW}--> Current Balance:{RESET} {GREEN}{user_balance}{RESET} {YELLOW}| Total Charges:{RESET} {GREEN}{charges}/{max_charges}{RESET}")
                
                return user_balance, charges
            else:
                print(f"{RED}Failed to fetch data: {response.status_code}{RESET}")
                response_body = response.text
                
                # Save response to a file if too long
                if len(response_body) > 1000:
                    with open("response_body.txt", "w", encoding="utf-8") as file:
                        file.write(response_body)
                    print("Response body saved to response_body.txt")
                else:
                    print("Response body:", response_body)
                print(f"Authentication: initData {query}")
                exit(1)

        except httpx.RequestError as e:
            print(f"{RED}An error occurred while making the request: {e}{RESET}")
            exit(1)

async def change_template(query_id, url):
    headers = {
        "Authorization": f"initData {query_id}"
    }
    response = requests.put(url, headers=headers)
    return response.status_code

async def paint(query_id, k):
    # Define the URL and headers for the repaint request
    url = 'https://notpx.app/api/v1/repaint/start'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"initData {query_id}"
    }

    # Define color data based on k's value
    data = {
        "pixelId": 271165,
        "newColor": "#000000" if k % 2 == 0 else "#9C6926"
    }

    # Send the repaint request and handle response
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            if 'balance' in response_data:
                balance = response_data['balance']
                return {
                    "balance": balance,
                    "pixelId": data["pixelId"],
                    "newColor": data["newColor"]
                }
            else:
                print(f"{RED}No balance information available.{RESET}")
        else:
            handle_error(response.status_code)
            return None, None, None  # Ensure to return None if there’s an error
    except requests.RequestException as error:
        print(f"{RED}An unexpected error occurred: {error}{RESET}")
        return None, None, None  # Ensure to return None if there’s an error

async def claim(query_id, acc_name, k: int):
    url = 'https://notpx.app/api/v1/mining/claim'
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': f"initData {query_id}",
        'Origin': 'https://app.notpx.app',
        'Referer': 'https://app.notpx.app/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an error for HTTP codes 4XX/5XX
        claimed= response.json().get('claimed')

        if k == 1:
            print(f"{BLUE}{acc_name}{RESET} {YELLOW}--> Successfully Claimed From Mining:{RESET} {GREEN}{claimed}{RESET} {YELLOW}px{RESET}")
        elif k == 2:
            print(f"{CYAN}{acc_name}{RESET} {YELLOW}--> Successfully Claimed From Mining:{RESET} {GREEN}{claimed}{RESET} {YELLOW}px{RESET}")

    except requests.exceptions.HTTPError as http_err:
        print(f'{RED}HTTP error occurred: {http_err}{RESET}')
    except Exception as err:
        print(f'{RED}An error occurred while claiming, or it has already been claimed: {err}{RESET}')

# Function to handle specific status codes for error handling
def handle_error(status_code):
    if status_code == 401:
        print(f"{RED}Your session has expired. Please re-authenticate.{RESET}")
    elif status_code == 400:
        print()
    elif status_code == 504:
        print(f"{RED}Upstream request timeout or unresponsive.{RESET}")
    else:
        print(f"{RED}\033[31mAn unexpected error occurred: {status_code}{RESET}")

async def notpixel_paint_and_claim(query1, query2, name1, name2):
    balance1, charges1 = await get_balance(query1, name1, 1)
    balance2, charges2 = await get_balance(query2, name2, 2)

    Total1= 0
    Total2= 0
    while True:
        flag1= False
        flag2= False
        # Call the paint function for both results
        result1 = await paint(query1, 1)
        result2 = await paint(query2, 2)

        # If either result is None, exit the loop
        if result1 is None or result2 is None:
            print(f"{YELLOW}Stopping loop: one or both results are None.{RESET}")
            break

        # Ensure results are dictionaries before unpacking
        if isinstance(result1, dict) and isinstance(result2, dict):
            paint_balance1, pixelId1, color1 = result1['balance'], result1['pixelId'], result1['newColor']
            paint_balance2, pixelId2, color2 = result2['balance'], result2['pixelId'], result2['newColor']
            
            # Define a small tolerance level
            epsilon = 1e-10  # Adjust this based on the precision you need

            # Perform the subtraction
            earned1 = paint_balance1 - balance1
            earned2 = paint_balance2 - balance2

            # Check if each result is close enough to zero, then set it to zero if so
            if abs(earned1) < epsilon:
                earned1 = 0.0
                flag1= True

            if abs(earned2) < epsilon:
                earned2 = 0.0
                flag2= True
            
            if flag1:
                print(f"{BLUE}{name1}{RESET} {RED}--> Unsuccessfully Painted: +{earned1} px | Balance: {paint_balance1} px | Pixel ID: {pixelId1} | Colour: {color1}{RESET}")
            elif flag2:
                print(f"{CYAN}{name2}{RESET} {RED}--> Unsuccessfully Painted: +{earned2} px | Balance: {paint_balance2} px | Pixel ID: {pixelId2} | Colour: {color2}{RESET}")
            else:
                print(f"{BLUE}{name1}{RESET} {GREEN}--> Successfully Painted:{RESET} {RED}+{earned1}{RESET} {GREEN}px | Balance:{RESET} {TEXT_CYAN}{paint_balance1}{RESET} {GREEN}px | Pixel ID:{RESET} {TEXT_CYAN}{pixelId1}{RESET} {GREEN}| Colour:{RESET} {TEXT_CYAN}{color1}{RESET}")
                print(f"{CYAN}{name2}{RESET} {GREEN}--> Successfully Painted:{RESET} {RED}+{earned2}{RESET} {GREEN}px | Balance:{RESET} {TEXT_CYAN}{paint_balance2}{RESET} {GREEN}px | Pixel ID:{RESET} {TEXT_CYAN}{pixelId2}{RESET} {GREEN}| Colour:{RESET} {TEXT_CYAN}{color2}{RESET}")

            # Update balances for next iteration
            balance1, balance2 = paint_balance1, paint_balance2
            Total1= Total1+earned1
            Total2= Total2+earned2
        else:
            break

    print(f"{BLUE}{name1}{RESET} {YELLOW}--> Totally Earned:{RESET} {GREEN}{Total1}{RESET}")
    print(f"{CYAN}{name2}{RESET} {YELLOW}--> Totally Earned:{RESET} {GREEN}{Total2}{RESET}")
    await claim(query1, name1, 1)
    await waiting(2)
    await claim(query2, name2, 2)

async def notpixel_play_game():
    with get_db_connection() as db:
        queries = db.execute('SELECT * FROM queries').fetchall()
        num_rows = len(queries)

        # Check if table is empty
        if num_rows == 0:
            print(f"{YELLOW}The queries table is empty.{RESET}")
        else:
            # Process rows in pairs
            for i in range(0, num_rows - 1, 2):
                # Get the current pair
                first_row = queries[i]
                second_row = queries[i + 1]
        
                # Extract values from each row in the pair
                proxy1, session1, user_id1, name1, bot_username1, query1 = first_row
                proxy2, session2, user_id2, name2, bot2_username2, query2 = second_row

                status1 = await change_template(query1, "https://notpx.app/api/v1/image/template/subscribe/1709562088")
                if status1 == 204:
                    print(f"{GREEN}Successfully Template Changed To Major Template..........{RESET}")
                elif status1 == 200 or status1 == 403:
                    print(f"{YELLOW}Major Template is already selected.{RESET}")
                else:
                    print(f"{RED}Unable to change major Template: {status1}{RESET}")

                status2 = await change_template(query2, "https://notpx.app/api/v1/image/template/subscribe/1972552043")
                if status2 == 204:
                    print(f"{GREEN}Successfully Template Changed To Okx Template..........{RESET}")
                elif status2 == 200 or status2 == 403:
                    print(f"{YELLOW}Okx Template is already selected{RESET}")
                else:
                    print(f"{RED}Unable to change Okx Template: {status2}{RESET}")

                await notpixel_paint_and_claim(query1, query2, name1, name2)
                print(f"{YELLOW}==============================================={RESET} {BLUE}Completed Session:{RESET} {TEXT_CYAN}{name1}{RESET} {YELLOW}AND{RESET} {TEXT_CYAN}{name2}{RESET} {YELLOW}==============================================={RESET}")

            # If there's an odd number of rows, handle the last row separately
            if num_rows % 2 != 0:
                last_row = queries[-1]
                proxy, session, user_id, name, bot_username, query = last_row
                print(f"{YELLOW}Single remaining row:{RESET} {TEXT_CYAN}{proxy}, {session}, {user_id}, {name}, {bot_username}, {query}{RESET}")

async def waiting(seconds):
    try:
        while seconds >= 0:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            sys.stdout.write(f"\033[90m\rWaiting For: {str(hours).zfill(2)}:{str(minutes).zfill(2)}:{str(secs).zfill(2)}\033[0m")
            sys.stdout.flush()

            await asyncio.sleep(1)
            seconds -= 1

        print()  # Move to the next line after completion
    except Exception as error:
        print(f"{RED}Error: {error}{RESET}")

# Example usage
if __name__ == '__main__':
    load_dotenv(find_dotenv())

    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')

    if api_id is None or api_hash is None:
        print(f"{RED}Error: API_ID and API_HASH must be set in the .env file.{RESET}")
        exit(1)

    if api_id.strip() == "" or api_hash.strip() == "":
        print(f"{RED}Error: API_ID and API_HASH cannot be empty.{RESET}")
        exit(1)

    try:
        api_id = int(api_id)
    except ValueError:
        print(f"{RED}Error: API_ID must be an integer.{RESET}")
        exit(1)
        
    init_db()  # Initialize the database once at startup
    init_db4()
    get_account_session_string_with_proxy()

    try:
        while True:
            asyncio.run(generate_queries_for_all_sessions())
            asyncio.run(notpixel_play_game())
            clear_queries()
            asyncio.run(waiting(7200))

    except KeyboardInterrupt:
        print(f"{RED}Process interrupted by user. Exiting gracefully...{RESET}")
    except RuntimeError as e:
        if 'Event loop stopped before Future completed' in str(e):
            print(f"{RED}Warning: The event loop was stopped before all tasks were completed. Exiting gracefully...{RESET}")
        else:
            print(f"{RED}Unexpected runtime error: {e}{RESET}")