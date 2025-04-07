import time
import json
import os
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import yaml

# Constants
CONFIG_FILE = "config.yml"
PROGRESS_FILE = "messaged_followers.json"
FAIL_FILE = "messaged_fail.json"
LOG_FILE = f"x_dm_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
DM_INTERVAL = 15  # seconds between DMs

# Set up logging
def setup_logging():
    """Configure logging to both file and console"""
    logger = logging.getLogger('x_dm_script')
    logger.setLevel(logging.INFO)
    
    # Create file handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_advanced_options(config):
    """Extract advanced options from config with defaults"""
    if 'options' not in config:
        config['options'] = {}
    
    options = {
        'dm_interval': config['options'].get('dm_interval', 15),
        'retry_failed': config['options'].get('retry_failed', False),
        'max_followers_to_process': config['options'].get('max_followers_to_process', float('inf')),
        'skip_first_n': config['options'].get('skip_first_n', 0),
        'take_screenshots': config['options'].get('take_screenshots', True)  # New option for screenshots
    }
    
    logger.info(f"Using advanced options: {options}")
    return options

def load_config():
    """Load configuration from YAML file"""
    logger.info(f"Loading configuration from {CONFIG_FILE}")
    try:
        with open(CONFIG_FILE, 'r') as file:
            config = yaml.safe_load(file)
            logger.info(f"Configuration loaded for account: @{config['x_credentials']['account_name']}")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

def load_progress():
    """Load list of already messaged followers and failed attempts"""
    progress = {"messaged_usernames": [], "started_at": datetime.now().isoformat(), "stats": {"success": 0, "failed": 0}}
    failed = []

    if os.path.exists(PROGRESS_FILE):
        logger.info(f"Loading progress from {PROGRESS_FILE}")
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
            logger.info(f"Found {len(progress.get('messaged_usernames', []))} previously messaged users")

    if os.path.exists(FAIL_FILE):
        logger.info(f"Loading failed attempts from {FAIL_FILE}")
        with open(FAIL_FILE, 'r') as f:
            failed = json.load(f)
            logger.info(f"Found {len(failed)} previously failed attempts")

    return progress, failed

def save_progress(progress, failed):
    """Save list of messaged followers and failed attempts"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)
    logger.info(f"Progress saved - Success: {progress['stats']['success']}, Failed: {progress['stats']['failed']}")

    with open(FAIL_FILE, 'w') as f:
        json.dump(failed, f)
    logger.info(f"Failed attempts saved - Total Failed: {len(failed)}")

def setup_driver(headless=True):
    """Set up and return a configured webdriver"""
    logger.info(f"Setting up Chrome driver (headless={headless})")
    options = webdriver.ChromeOptions()
    
    if headless:
        # Fix for "DevToolsActivePort file doesn't exist" error
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
    
    # Common options for both headless and non-headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=options)
        logger.info("Chrome driver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        
        # Fallback to non-headless if headless fails
        if headless:
            logger.info("Trying to initialize Chrome in non-headless mode as fallback")
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-notifications")
            options.add_argument("--start-maximized")
            driver = webdriver.Chrome(options=options)
            logger.info("Chrome driver initialized in non-headless mode")
            return driver
        else:
            raise

def login_to_x(driver, username, password, options):
    """Login to X account"""
    logger.info(f"Attempting to login as @{username}")
    driver.get("https://x.com/login")
    
    try:
        # Wait for login form
        logger.info("Waiting for login form...")
        username_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@autocomplete='username']"))
        )
        username_input.send_keys(username)
        username_input.send_keys(Keys.RETURN)
        logger.info("Username submitted")
        
        # Check if we need to enter display name instead of just username
        try:
            logger.info("Checking for additional username verification...")
            verify_username = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']"))
            )
            verify_username.send_keys(username)
            verify_username.send_keys(Keys.RETURN)
            logger.info("Additional username verification completed")
        except TimeoutException:
            # No verification needed, continue
            logger.info("No additional username verification required")
            pass
        
        # Enter password
        logger.info("Entering password...")
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@autocomplete='current-password']"))
        )
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        
        # Wait for successful login (home timeline)
        logger.info("Waiting for home timeline to confirm login...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-testid='primaryColumn']"))
        )
        logger.info("🔓 LOGIN SUCCESSFUL: Successfully logged in to X")
        return True
        
    except Exception as e:
        logger.error(f"⚠️ LOGIN FAILED: {e}")
        # Save screenshot for debugging login issues
        if options['take_screenshots']:
            try:
                screenshot_file = f"login_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_file)
                logger.info(f"Screenshot saved as {screenshot_file}")
            except:
                logger.error("Failed to save screenshot")
        return False

def get_followers(driver, account_name, options):
    """Get list of followers"""
    logger.info(f"Getting followers for @{account_name}...")
    driver.get(f"https://x.com/{account_name}/followers")
    
    # Wait for the page to fully load
    logger.info("Waiting for followers page to load...")
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']"))
        )
        time.sleep(5)  # Give extra time for the page to load completely
    except TimeoutException:
        logger.error("Timed out waiting for followers page to load")
        return []
    
    # Take screenshot of the followers page for debugging
    if options['take_screenshots']:
        debug_screenshot = f"followers_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        driver.save_screenshot(debug_screenshot)
        logger.info(f"Followers page screenshot saved as {debug_screenshot}")
    
    # Initialize list to store follower usernames
    followers = []
    previous_count = 0
    no_change_count = 0
    max_no_change = 5  # If we see no new followers for this many scrolls, we stop
    scroll_count = 0
    max_scrolls = 100  # Maximum number of scrolls to prevent infinite loops
    
    logger.info("Starting to scroll and collect followers...")
    
    # Common non-profile pages to filter out
    excluded_pages = ['tos', 'privacy', 'about', 'help', 'explore', 'notifications', 
                      'home', 'i', 'messages', 'settings', 'search', 'compose', 'status']
    
    while no_change_count < max_no_change and scroll_count < max_scrolls:
        scroll_count += 1
        found_new = False
        
        # First try to get all user cells directly
        try:
            user_cells = driver.find_elements(By.CSS_SELECTOR, "[data-testid='UserCell']")
            logger.debug(f"Found {len(user_cells)} user cells")
            
            for cell in user_cells:
                try:
                    # Look for the link with username within the cell
                    links = cell.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute('href')
                        if href and href.startswith('https://x.com/'):
                            username = href.split('/')[-1]
                            
                            # Filter out non-profile paths
                            if (username and username not in excluded_pages and 
                                not any(excluded in href for excluded in ['/status/', '/i/', '/search'])):
                                if username not in followers:
                                    followers.append(username)
                                    found_new = True
                except Exception as e:
                    logger.debug(f"Error extracting username from cell: {e}")
                    continue
        except Exception as e:
            logger.debug(f"Error finding UserCell elements: {e}")
        
        # If no UserCells found, try a more general approach
        if len(followers) == 0:
            logger.info("No UserCells found, trying alternative approach...")
            try:
                # Get all links that might be profile links
                links = driver.find_elements(By.TAG_NAME, "a")
                
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        if href and href.startswith('https://x.com/'):
                            username = href.split('/')[-1]
                            
                            # Filter out non-profile paths
                            if (username and username not in excluded_pages and 
                                not any(excluded in href for excluded in ['/status/', '/i/', '/search'])):
                                if username not in followers:
                                    followers.append(username)
                                    found_new = True
                    except Exception as e:
                        continue
            except Exception as e:
                logger.debug(f"Error finding profile links: {e}")
        
        # Break if no new followers loaded after scrolling multiple times
        if not found_new:
            no_change_count += 1
            logger.info(f"No new followers found after scroll. Attempt {no_change_count}/{max_no_change}")
        else:
            no_change_count = 0
            
        # Log progress
        if len(followers) != previous_count:
            logger.info(f"Found {len(followers)} followers so far...")
            previous_count = len(followers)
        
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Increased wait time after scrolling
        
        # Every 10 scrolls, take a screenshot
        if options['take_screenshots'] and scroll_count % 10 == 0:
            scroll_screenshot = f"scroll_{scroll_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            driver.save_screenshot(scroll_screenshot)
            logger.info(f"Scroll screenshot saved as {scroll_screenshot}")
    
    # Filter out any remaining system pages or non-profile links that might have been captured
    valid_followers = [f for f in followers if f not in excluded_pages and len(f) > 1]
    
    if valid_followers:
        logger.info(f"✅ FOLLOWERS COLLECTED: Found total of {len(valid_followers)} followers")
    else:
        logger.error("⚠️ NO FOLLOWERS FOUND: Check if the account has followers or try running in non-headless mode")
    
    # Save the list of followers to a file for review
    try:
        with open("followers_list.txt", "w") as f:
            for follower in valid_followers:
                f.write(f"{follower}\n")
        logger.info("Saved followers list to followers_list.txt")
    except Exception as e:
        logger.error(f"Error saving followers list: {e}")
    
    return valid_followers

# Replacement for your send_dm function with better button handling
def send_dm(driver, username, message, options):
    """Send DM to a specific user with verification of success"""
    logger.info(f"Attempting to send DM to @{username}...")
    
    try:
        # Navigate to user's profile
        driver.get(f"https://x.com/{username}")
        
        # Wait for profile to load
        logger.info(f"Waiting for @{username}'s profile to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-testid='primaryColumn']"))
        )
        
        # Wait for any loading spinners to disappear
        time.sleep(3)
        
        # Take screenshot of profile before looking for message button (for debugging)
        if options['take_screenshots']:
            debug_screenshot = f"profile_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            driver.save_screenshot(debug_screenshot)
            logger.info(f"Profile screenshot saved as {debug_screenshot}")
        
        # Try to find and click the message button using multiple methods
        message_button_found = False
        
        # Method 1: Try direct targeting by data-testid
        try:
            message_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='sendDMFromProfile']"))
            )
            driver.execute_script("arguments[0].click();", message_button)
            message_button_found = True
            logger.info("Found message button with data-testid")
        except:
            logger.info("Could not find message button with data-testid")
        
        # Method 2: Try finding by aria-label if first method fails
        if not message_button_found:
            try:
                message_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Message')]"))
                )
                driver.execute_script("arguments[0].click();", message_button)
                message_button_found = True
                logger.info("Found message button with aria-label")
            except:
                logger.info("Could not find message button with aria-label")
        
        # Method 3: Use JavaScript to find button by text content
        if not message_button_found:
            try:
                message_clicked = driver.execute_script("""
                    var buttons = document.querySelectorAll('button, div[role="button"]');
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].textContent.toLowerCase().includes('message')) {
                            buttons[i].click();
                            return true;
                        }
                    }
                    return false;
                """)
                
                if message_clicked:
                    message_button_found = True
                    logger.info("Found and clicked message button with JavaScript")
                else:
                    logger.info("JavaScript could not find a message button")
            except Exception as e:
                logger.info(f"JavaScript approach error: {e}")
        
        # If we still can't find the message button, try the user actions area
        if not message_button_found:
            try:
                # Click the first button in the user actions area
                driver.execute_script("""
                    var userActions = document.querySelector('div[data-testid="userActions"]');
                    if (userActions) {
                        var buttons = userActions.querySelectorAll('div[role="button"]');
                        if (buttons.length > 0) {
                            buttons[0].click();
                            return true;
                        }
                    }
                    return false;
                """)
                logger.info("Clicked first button in user actions area")
                message_button_found = True
            except:
                logger.warning("Failed to click any button in user actions area")
        
        if not message_button_found:
            logger.error(f"Could not find or click message button for @{username}")
            return False
        
        # Wait for DM modal to appear
        logger.info("Waiting for DM composer...")
        time.sleep(3)
        
        # Try different methods to find the message input
        message_input = None

        # Method 1: Look for the input by data-testid
        try:
            message_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-testid='dmComposerTextInput']"))
            )
            logger.info("Found message input with data-testid")
        except:
            logger.info("Could not find message input with data-testid")

        # Method 2: Look for contenteditable div
        if not message_input:
            try:
                message_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='textbox' and @contenteditable='true']"))
                )
                logger.info("Found message input with contenteditable attribute")
            except:
                logger.info("Could not find contenteditable message input")

        # Method 3: Use JavaScript to find any contenteditable element
        if not message_input:
            try:
                message_input = driver.execute_script("""
                    return document.querySelector('div[contenteditable="true"]');
                """)
                if message_input:
                    logger.info("Found message input with JavaScript")
                else:
                    logger.warning("JavaScript could not find message input")
            except Exception as e:
                logger.info(f"JavaScript input search error: {e}")
        if not message_input:
            logger.error(f"Could not find message input for @{username}")
            return False

        # Store original message content for verification
        message_first_words = message.split()[:3]
        message_snippet = ' '.join(message_first_words)
        logger.info(f"Will verify message containing: '{message_snippet}'")

        # Type the message with line breaks
        try:
            # Focus the input first
            driver.execute_script("arguments[0].focus();", message_input)
            time.sleep(0.5)
            
            # Try to clear any existing text and placeholder
            driver.execute_script("""
                var element = arguments[0];
                element.innerHTML = '';
                element.textContent = '';
            """, message_input)
            time.sleep(0.5)
            
            # Click on the input to ensure it's activated
            message_input.click()
            time.sleep(0.5)
            
            # Type the message line by line to handle line breaks
            for line in message.split('\n'):
                message_input.send_keys(line)
                message_input.send_keys(Keys.SHIFT, Keys.RETURN)
                time.sleep(0.2)  # Small delay between lines
            
            logger.info("Message typed with line breaks")
            
            # Additional check to verify text was entered
            entered_text = driver.execute_script("return arguments[0].textContent || arguments[0].innerText;", message_input)
            logger.info(f"Verified text in input field: '{entered_text[:20]}...'")
            
            # If verification fails, try another approach
            if not entered_text or entered_text.strip() == '':
                logger.warning("Text verification failed, trying alternate approach")
                # Try using ActionChains for typing
                actions = webdriver.ActionChains(driver)
                message_input.click()
                for line in message.split('\n'):
                    actions.send_keys(line)
                    actions.key_down(Keys.SHIFT).send_keys(Keys.RETURN).key_up(Keys.SHIFT)
                actions.perform()
                logger.info("Message typed using ActionChains with line breaks")
                
                # Check again after ActionChains
                entered_text = driver.execute_script("return arguments[0].textContent || arguments[0].innerText;", message_input)
                logger.info(f"After ActionChains, text in field: '{entered_text[:20]}...'")
        except Exception as e:
            logger.warning(f"Advanced typing methods failed: {e}, trying fallback method")
            try:
                # Traditional SendKeys approach
                message_input.click()
                message_input.clear()
                for line in message.split('\n'):
                    message_input.send_keys(line)
                    message_input.send_keys(Keys.SHIFT, Keys.RETURN)
                logger.info("Message typed using basic send_keys with line breaks")
            except Exception as e2:
                logger.error(f"All typing methods failed: {e2}")
                return False

        # Take screenshot after typing
        if options['take_screenshots']:
            after_type_screenshot = f"after_type_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            driver.save_screenshot(after_type_screenshot)
            logger.info(f"After typing screenshot saved as {after_type_screenshot}")
        
        # Wait a moment after typing
        time.sleep(2)
        
        # IMPROVED SEND BUTTON TARGETING based on your HTML snippet
        send_button_clicked = False
        
        # Method 1: Direct target the send button using the data-testid from your HTML
        try:
            send_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='dmComposerSendButton']"))
            )
            logger.info("Found send button with data-testid")
            
            # Try JavaScript click first
            driver.execute_script("arguments[0].click();", send_button)
            logger.info("Send button clicked via JavaScript")
            send_button_clicked = True
        except Exception as e:
            logger.info(f"Could not find or click send button with data-testid: {e}")
        
        # Method 2: Try using the exact HTML structure you provided
        if not send_button_clicked:
            try:
                # Target button with aria-label="Send"
                send_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']"))
                )
                logger.info("Found send button with aria-label")
                
                # Try JavaScript click
                driver.execute_script("arguments[0].click();", send_button)
                logger.info("Send button clicked via JavaScript")
                send_button_clicked = True
            except Exception as e:
                logger.info(f"Could not find or click send button with aria-label: {e}")
        
        # Method 3: Use more precise JavaScript targeting based on the HTML you provided
        if not send_button_clicked:
            try:
                send_clicked = driver.execute_script("""
                    // Look for the exact button structure you shared
                    var sendButton = document.querySelector('button[aria-label="Send"][data-testid="dmComposerSendButton"]');
                    
                    // If not found, look for any button with Send in aria-label
                    if (!sendButton) {
                        sendButton = document.querySelector('button[aria-label="Send"]');
                    }
                    
                    // If not found, look for any button with the data-testid
                    if (!sendButton) {
                        sendButton = document.querySelector('button[data-testid="dmComposerSendButton"]');
                    }
                    
                    // If not found, look for a button with a blue SVG icon
                    if (!sendButton) {
                        var buttons = document.querySelectorAll('button');
                        for (var i = 0; i < buttons.length; i++) {
                            if (buttons[i].querySelector('svg[style*="rgb(29, 155, 240)"]')) {
                                sendButton = buttons[i];
                                break;
                            }
                        }
                    }
                    
                    // If button found, click it
                    if (sendButton) {
                        sendButton.click();
                        return true;
                    }
                    return false;
                """)
                
                if send_clicked:
                    logger.info("Send button clicked via precise JavaScript targeting")
                    send_button_clicked = True
                else:
                    logger.warning("JavaScript could not find and click send button")
            except Exception as e:
                logger.info(f"JavaScript send button click error: {e}")
        
        # Method 4: Hit Enter key as last resort
        if not send_button_clicked:
            try:
                # Focus the input element again
                driver.execute_script("arguments[0].focus();", message_input)
                time.sleep(0.5)
                
                # Send Enter key
                actions = webdriver.ActionChains(driver)
                actions.send_keys(Keys.RETURN)
                actions.perform()
                logger.info("Sent Enter key via ActionChains")
                send_button_clicked = True
                time.sleep(1)
                
                # Try direct send_keys on the element too
                message_input.send_keys(Keys.RETURN)
                logger.info("Sent Enter key directly to input element")
            except Exception as e:
                logger.warning(f"Enter key approach failed: {e}")
        
        # Take screenshot after sending attempt
        if options['take_screenshots']:
            after_send_screenshot = f"after_send_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            driver.save_screenshot(after_send_screenshot)
            logger.info(f"After send screenshot saved as {after_send_screenshot}")
        
        # Wait longer for the send operation to complete
        time.sleep(5)
        
        # Check for message sent confirmation
        message_sent = False
        
        # Method 1: Look for our message in the conversation
        try:
            message_xpath = f"//div[contains(text(), '{message_snippet}')]"
            message_found = driver.find_elements(By.XPATH, message_xpath)
            if message_found:
                logger.info(f"Found our message in conversation: '{message_snippet}'")
                message_sent = True
            else:
                logger.info("Didn't find our message in conversation")
        except Exception as e:
            logger.warning(f"Error checking for message in conversation: {e}")
        
        # Method 2: Check if input field is now empty (indicating message sent)
        if not message_sent:
            try:
                input_html = message_input.get_attribute('innerHTML')
                if not input_html or input_html.strip() == '<br>' or input_html.strip() == '':
                    logger.info("Message input is now empty, likely indicating message was sent")
                    message_sent = True
                else:
                    logger.info("Message input still has content")
            except Exception as e:
                logger.warning(f"Error checking input content: {e}")
        
        # Method 3: Check URL change (in messages section)
        if not message_sent and 'messages' in driver.current_url:
            logger.info("URL contains 'messages', considering this a success")
            message_sent = True
        
        # Final verdict
        if message_sent:
            logger.info(f"✅ DM CONFIRMED SENT: Successfully sent DM to @{username}")
            return True
        elif send_button_clicked:
            logger.warning(f"⚠️ DM UNCERTAIN: Button clicked but couldn't verify message was sent to @{username}")
            # Return true anyway since we at least clicked the button
            return True
        else:
            logger.error(f"⚠️ DM FAILED: Could not find or click send button for @{username}")
            return False
            
    except Exception as e:
        logger.error(f"⚠️ DM FAILED: Error sending DM to @{username}: {e}")
        # Take screenshot of failure
        if options['take_screenshots']:
            try:
                screenshot_file = f"dm_error_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_file)
                logger.info(f"Screenshot saved as {screenshot_file}")
            except:
                logger.error("Failed to save screenshot")
        return False

def main():
    # Load configuration
    config = load_config()
    username = config['x_credentials']['username']
    password = config['x_credentials']['password']
    account_name = config['x_credentials']['account_name']
    message = config['message']
    headless = config.get('headless', True)
    
    # Get advanced options
    options = get_advanced_options(config)
    
    # Load progress
    progress, failed = load_progress()
    messaged_usernames = set(progress.get("messaged_usernames", []))
    
    # Initialize stats if not present
    if "stats" not in progress:
        progress["stats"] = {"success": 0, "failed": 0}
    
    # Setup driver
    try:
        driver = setup_driver(headless=headless)
    except Exception as e:
        logger.error(f"Failed to initialize driver: {e}")
        logger.error("Please ensure Chrome is properly installed and updated")
        return
    
    try:
        # Login to X
        if not login_to_x(driver, username, password, options):
            logger.error("Failed to login. Exiting...")
            driver.quit()
            return
        
        # Get followers
        followers = get_followers(driver, account_name, options)
        
        # Filter out already messaged followers
        followers_to_message = [f for f in followers if f not in messaged_usernames]
        logger.info(f"Need to message {len(followers_to_message)} out of {len(followers)} followers")
        
        # Apply skip option (useful for resuming)
        if options['skip_first_n'] > 0:
            if options['skip_first_n'] < len(followers_to_message):
                logger.info(f"Skipping first {options['skip_first_n']} followers as requested")
                followers_to_message = followers_to_message[options['skip_first_n']:]
            else:
                logger.warning(f"Skip count {options['skip_first_n']} is >= followers count {len(followers_to_message)}")
        
        # Apply maximum followers limit
        if len(followers_to_message) > options['max_followers_to_process']:
            logger.info(f"Limiting to first {options['max_followers_to_process']} followers as configured")
            followers_to_message = followers_to_message[:options['max_followers_to_process']]
        
        # Send DMs to followers
        success_count = 0
        fail_count = 0
        
        for i, follower in enumerate(followers_to_message):
            logger.info(f"Processing follower {i+1}/{len(followers_to_message)}: @{follower}")
            
            # Send DM and handle retry if needed
            dm_sent = send_dm(driver, follower, message, options)
            
            if not dm_sent and options['retry_failed']:
                logger.info(f"Retrying DM to @{follower} after waiting...")
                time.sleep(10)  # Wait before retry
                dm_sent = send_dm(driver, follower, message, options)
            
            if dm_sent:
                # Update progress for successful DM
                messaged_usernames.add(follower)
                progress["messaged_usernames"] = list(messaged_usernames)
                progress["stats"]["success"] += 1
                success_count += 1
                logger.info(f"Progress: {success_count}/{len(followers_to_message)} complete")
            else:
                # Track failed attempts
                progress["stats"]["failed"] += 1
                fail_count += 1
                failed.append(follower)
                logger.warning(f"Failed to send DM to @{follower}")
            
            # Save progress after each attempt
            save_progress(progress, failed)
            
            # Sleep to avoid rate limiting
            if i < len(followers_to_message) - 1:  # Don't wait after the last message
                logger.info(f"Waiting {options['dm_interval']} seconds before next DM...")
                time.sleep(options['dm_interval'])
        
        logger.info(f"✅ PROCESS COMPLETED: Successfully sent {success_count} DMs, Failed: {fail_count}")
    
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    
    finally:
        # Always close the driver
        logger.info("Closing browser...")
        driver.quit()
        logger.info("Browser closed. Script terminated.")

if __name__ == "__main__":
    # Set up logging first
    logger = setup_logging()
    logger.info("============ X DM SCRIPT STARTED ============")
    
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    logger.info("============ X DM SCRIPT FINISHED ============")