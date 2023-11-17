import datetime
import json
import os

from metaphor_python import Metaphor

METAPHOR_API_KEY = os.getenv("METAPHOR_API_KEY")
if METAPHOR_API_KEY is None:
    raise Exception("METAPHOR_API_KEY not found in environment variables")

URLS_TO_SEARCH = [
    "https://danielsgriffin.com/hire-me/",
    "https://danielsgriffin.com/research/",
    "https://danielsgriffin.com/about/",
    "https://danielsgriffin.com/diss/",
    "https://danielsgriffin.com/publications/",
]


def check_if_searched_recently(url, recency_check=7):
    """Check if a URL has been searched in the last recency_check days."""
    # Load the existing log
    filename = "similar_pages_log.json"
    try:
        with open(filename, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    # Get latest datestamp for the URL
    latest_datestamp = ""
    if url in data:
        latest_datestamp = max(data[url], default="")
    if latest_datestamp == "":
        return False
    # conduct the check (default is 7 days)
    # get the date for recency_check days ago
    recency_check_date = (
        datetime.datetime.utcnow() - datetime.timedelta(days=recency_check)
    ).strftime("%Y-%m-%d")
    if latest_datestamp[:10] >= recency_check_date:
        return True
    return False


def find_similar_pages(url, num_results=10, start_published_date=None):
    # Skip the search if there is a log entry for the current date for the URL
    recency_check = 7
    if check_if_searched_recently(url, recency_check=recency_check):
        return [f"Skipped: Already searched {url} within the last {recency_check} days."]

    # Initialize the Metaphor API client
    metaphor = Metaphor(METAPHOR_API_KEY)

    # Prepare the options for the API call
    options = {
        "exclude_source_domain": True,
        "num_results": num_results,  # Set the number of results
    }
    if start_published_date:
        options["start_published_date"] = start_published_date

    # Find similar pages excluding the same domain
    print(f"Searching for similar pages...: {url}")
    try:
        response = metaphor.find_similar(url, **options)
        return response.results
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def log_similar_pages(similar_pages, url_to_search):
    # Load the existing log
    filename = "similar_pages_log.json"
    try:
        with open(filename, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    # Add the new pages to the log
    datestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")
    if url_to_search not in data:
        data[url_to_search] = {}
    data[url_to_search][datestamp] = []
    for page in similar_pages:
        data[url_to_search][datestamp].append(
            {"title": page.title, "url": page.url, "score": page.score}
        )

    # Save the updated log
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


from collections import defaultdict


def check_for_new_pages_in_log():
    try:
        # Load the log
        with open("similar_pages_log.json", "r") as file:
            log = json.load(file)
            raw_text = json.dumps(log)  # Convert the entire JSON to raw text
    except Exception as e:
        print(f"Failed to load the log: {e}")
        return

    print("Log loaded successfully.")

    # Get URLs from the most recent entries
    report_dict = defaultdict(list)
    for url_to_search in log:
        most_recent_urls = []
        most_recent_datestamp = max(log[url_to_search], default="")
        most_recent_entries = log[url_to_search].get(most_recent_datestamp, [])
        for page in most_recent_entries:
            most_recent_urls.append(page["url"])

        # Check if URLs appear only once in the raw text
        for url in most_recent_urls:
            if raw_text.count(url) == 1:
                # get the title from the url
                title = ""
                for page in most_recent_entries:
                    if page["url"] == url:
                        title = page["title"]
                        break
                report_dict[url_to_search].append(f"{title} at {url}")

    # Print the report
    if report_dict:
        print("#" * 80)
        print("New pages found:")
        for url_to_search in report_dict:
            print(f"  - URL searched: {url_to_search}")
            for new_page in report_dict[url_to_search]:
                print(f"    - {new_page}")


def main():
    start_published_date = (
        datetime.datetime.now() - datetime.timedelta(days=30)
    ).strftime(
        "%Y-%m-%d"
    )  # ISO 8601 format date string one month prior to current date
    num_results = 10  # Number of results you want to fetch

    for url_to_search in URLS_TO_SEARCH:
        # Fetch similar pages
        similar_pages = find_similar_pages(
            url_to_search, num_results, start_published_date
        )
        # If skipped message is returned, print it and continue
        try:
            if similar_pages[0].startswith("Skipped"):
                print(similar_pages[0])
                continue
        except AttributeError:
            log_similar_pages(similar_pages, url_to_search)
            print(f"Found {len(similar_pages)} similar pages for {url_to_search}")
            # print the results
            print(f"Results for {url_to_search}:")
            for page in similar_pages:
                print(
                    f"Title: {page.title}, URL: {page.url}, Score: {page.score if page.score is not None else 'N/A'}"
                )

            print(f"Results logged in similar_pages_log.json")
    check_for_new_pages_in_log()


if __name__ == "__main__":
    main()