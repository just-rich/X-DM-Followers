# X DM Followers
**Warning: This script may breach X's Terms of Service contract that you agreed to when creating an account. It was made for educational & informational purposes.**

This project is a Python script designed to send direct messages (DMs) to followers on X (formerly known as Twitter) using a headless browser. The script logs into your X account, fetches a list of your followers, and sends a predefined message to each follower.

## Features

- **Headless Browser**: Uses Selenium with a headless Chrome browser for automation.
- **Configurable**: Allows customization of DM intervals, retry attempts, maximum followers to process, and more via a config file.
- **Progress Tracking**: Saves progress to avoid messaging the same follower more than once.
- **Screenshot Option**: Can take screenshots at various stages for debugging purposes.
- **Message Verification**: Verifies the message by checking the first few words of the predefined message in the DM. *(Current version has some issues with this, but still knows when it's a success)*

## Requirements

- Python 3.6 or higher
- Chrome browser
- ChromeDriver

## Dependencies

Install the required Python packages using `pip`:

```bash
python -m pip install requirements.txt
```

## Configuration

Copy `example.config.yml` and replace *username*, *password*, & *account_name* with your X account credentials. Below is an example configuration:

```yaml
x_credentials:
  username: "username_here"  # Your X login username
  password: "pass_here"  # Your X login password
  account_name: "username_here"  # Your X account name (for getting followers)

message: "Hey follower! Please follow our primary/main account at @PrimaryAccount\n\nWe had to switch accounts, so would greatly appreciate if you followed the other. You can unfollow this one after too, if you prefer it."

headless: true  # Set to false if you want to see the browser

# Advanced options
options:
  dm_interval: 10  # Seconds between DMs
  retry_failed: true  # Retry failed DMs once
  max_followers_to_process: 2500  # Limit number of followers to process
  skip_first_n: 0  # Skip the first N followers (useful to resume after errors)
  take_screenshots: true  # Enable or disable taking screenshots
```

## How It Works

1. **Load Configuration**: Reads the configuration from `config.yml`.
2. **Initialize WebDriver**: Sets up the Chrome WebDriver with the specified options.
3. **Login**: Logs into your X account using the provided credentials.
4. **Fetch Followers**: Retrieves a list of your followers.
5. **Send DMs**: Sends a predefined message to each follower.
6. **Save Progress**: Tracks progress to avoid messaging the same follower more than once.
7. **Verify Message**: Verifies the message by checking the first few words of the predefined message in the DM.

## Usage

1. **Set Up Configuration**: Ensure the `config.yml` file is correctly configured with your X credentials and message.
2. **Run the Script**: Execute the script using Python.

```bash
python main.py
```

## Logging

The script logs its activities to a file named `x_dm_script_<timestamp>.log` and also outputs to the console. This log file is useful for debugging and tracking the script's progress.

## Screenshots

If the `take_screenshots` option is enabled, the script will save screenshots at various stages, such as login errors, profile views, and after sending DMs. These screenshots are saved in the root directory of the project with descriptive filenames. **You will want to set this to `false` after any debugging and it's working correctly, otherwise these images will take up a lot of space.**

## Troubleshooting

- **ChromeDriver Errors**: Ensure that ChromeDriver is installed and the version matches your Chrome browser version.
- **Login Issues**: Check the log file for errors during login. Ensure your credentials are correct.
- **Rate Limiting**: If you encounter rate limiting, increase the `dm_interval` in the configuration file.
- **DM Limits:** X has a DM limit for non-premium accounts. Once this limit is reached, with this current version of the code, it's very possible the app will think it's successfully sending DMs when it's really not.

## Contributing

Feel free to fork this project and submit pull requests.

## To Do / Notes
- If a follower has sent you a DM and you haven't accepted the message, it will fail to send that user a DM.
- Regarding this error, "WARNING - Error checking input content: Message: stale element reference: stale element not found in the current frame", it may happen requently and the DM might not be verified but it does send the message.

## License

This project is licensed under the [MIT License](LICENSE).

### Author

slapped together by [rich](https://richw.xyz)