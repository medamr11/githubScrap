from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# User Inputs
link_GitHub = input("Enter your GitHub Repository Link to search: ")
word_to_search = input("Enter the word to search for: ")
case_sensitive = input("Case sensitive search? (y/n): ").lower() == 'y'
max_depth = int(input("Maximum folder depth to search (e.g., 5): ") or "5")
file_extensions = input("File extensions to search (comma separated, leave empty for all): ")



# Parse file extensions
if file_extensions:
    extensions_list = [ext.strip().lower() for ext in file_extensions.split(',')]
    if not all(ext.startswith('.') for ext in extensions_list):
        extensions_list = ['.' + ext if not ext.startswith('.') else ext for ext in extensions_list]
else:
    extensions_list = [] # Empty list means search all files

if not link_GitHub.startswith("https://"):
    print("Invalid GitHub link!")
    exit()

if not word_to_search:
    print("Search word cannot be empty!")
    exit()

# Set up the search term based on case sensitivity
search_term = word_to_search if case_sensitive else word_to_search.lower()

# Path to ChromeDriver
try:
    service = Service(executable_path=r"C:\selenium\chromedriver.exe")  # Change as needed
    driver = webdriver.Chrome(service=service)
except Exception as e:
    print(f"Error setting up WebDriver: {e}")
    print("Trying without explicit driver path...")
    driver = webdriver.Chrome()  # Try with system default ChromeDriver

visited_links = set()  # To avoid revisiting
found_count = 0  # Counter for found matches

# Open the repository
try:
    driver.get(link_GitHub)
    print(f"📂 Starting search in: {link_GitHub}")
    print(f"🔍 Looking for: '{word_to_search}' (Case sensitive: {case_sensitive})")
    if extensions_list:
        print(f"📄 File types: {', '.join(extensions_list)}")
    else:
        print("📄 Searching all file types")
    print(f"⏱️ Max depth: {max_depth}")
    print("-" * 50)
except Exception as e:
    print(f"Failed to open repository: {e}")
    driver.quit()
    exit()

def find_repository(github_link):
    repositories = driver.find_elements(By.CLASS_NAME, 'repo')
    if repositories:
        print("Chose the  repository to scarp in :")
        for link in repositories:
            print(f"[•] {link.text}")
        right_repo=input("Enter the repository name :")
        if right_repo not in [link.text for link in repositories]:
            print("Wrong repository name")
            exit()
        for link in repositories:
            if right_repo == link.text:
                link.click()
                print(f"Accessing the repository  {link.text}")
                return link
    else:
        return github_link

find_repository(link_GitHub)

def is_target_file(link):
    """Check if the link points to a file we want to search."""
    if '/blob/' not in link:  # Not a file
        return False

    if not extensions_list:  # If no specific extensions, search all files
        return True

    # Check if the file has one of the specified extensions
    return any(link.lower().endswith(ext) for ext in extensions_list)


def search_in_repository(current_depth=0):
    """Recursively search for the word in all files and folders."""
    global found_count

    if current_depth > max_depth:
        print(f"⚠️ Reached maximum depth of {max_depth}. Backtracking...")
        return False

    try:
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//a[contains(@class, "Link--primary")]'))
        )

        # Get all relevant links
        elements = driver.find_elements(By.XPATH, '//a[contains(@class, "Link--primary")]')

        folder_links = []
        files_links = []

        # Extract correct links using JavaScript to handle encoding issues
        for element in elements:
            try:
                link = driver.execute_script("return arguments[0].href;", element)
                if not link or link in visited_links:  # Skip visited or invalid links
                    continue

                visited_links.add(link)  # Mark as visited

                if is_target_file(find_repository(link)):  # File link
                    files_links.append(link)
                elif '/tree/' in link:  # Folder link
                    folder_links.append(link)
            except Exception as e:
                print(f"⚠️ Error processing link: {e}")
                continue

        # Process all file links
        for file_link in files_links:
            try:
                driver.get(file_link)  # Open the file page
                print(f"📄 Checking file: {file_link}")

                # Wait for the raw button and fetch the content
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//a[@data-testid="raw-button"]'))
                    )

                    raw_button = driver.find_element(By.XPATH, '//a[@data-testid="raw-button"]')
                    raw_button.click()

                    # Get the content
                    html_content = driver.page_source

                    # Perform search
                    if case_sensitive:
                        found = word_to_search in html_content
                    else:
                        found = word_to_search.lower() in html_content.lower()

                    if found:
                        found_count += 1
                        print(f"✅ Success! Found '{word_to_search}' in >>> {file_link} <<<")

                        # Optional: return True to stop after first match
                        # return True
                    else:
                        print(f"❌ Word not found in: {file_link}")

                    driver.back()  # Go back to the file list
                except Exception as e:
                    print(f"⚠️ Error viewing raw content: {e}")
                    driver.back()
            except Exception as e:
                print(f"⚠️ Error processing file {file_link}: {e}")
                try:
                    driver.back()
                except:
                    driver.get(link_GitHub)  # Go back to main repo if navigation fails
                continue

        # Process all folder links
        for folder_link in folder_links:
            try:
                print(f"📂 Entering folder: {folder_link} (depth: {current_depth + 1})")
                driver.get(folder_link)  # Open the folder
                if search_in_repository(current_depth + 1):  # Recursive call with increased depth
                    return True
            except Exception as e:
                print(f"⚠️ Error entering folder {folder_link}: {e}")
                continue

        return found_count > 0  # Return True if any matches were found

    except Exception as e:
        print(f"⚠️ Error in repository search: {e}")
        return False


try:
    # Start searching
    found = search_in_repository()

    print("\n" + "=" * 50)
    if found_count > 0:
        print(f"✅ Search complete! Found '{word_to_search}' in {found_count} files.")
    else:
        print(f"❌ Word not found in any file.")
    print(f"🔍 Visited {len(visited_links)} links during search.")
    print("=" * 50)
except KeyboardInterrupt:
    print("\n\n⚠️ Search interrupted by user.")
except Exception as e:
    print(f"\n\n⚠️ Unexpected error: {e}")
finally:
    # Close the driver

    print("Closing browser...")
    driver.quit()