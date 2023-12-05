import time
import bs4
import requests
from bs4 import BeautifulSoup
import csv
import logging


def http_client():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                          " AppleWebKit/537.36 (KHTML, like Gecko)"
                          "Chrome/119.0.0.0 Safari/537.36"
        }
    )

    def log_url(res, *args, **kwargs):
        logging.info(f"{res.url}, {res.status_code}")

    session.hooks["response"] = log_url
    return session


def open_asins_from_file(filename: str):
    logging.info(f"opening {filename}")
    lines = []
    with open(filename, newline='') as f:
        reader = csv.reader(f)
        data = list(reader)
        for line in data:
            lines.append(line[0])
    return lines


def make_request(client, baseurl: str, asin: str):
    try:
        response = client.get(f"{baseurl}/dp/{asin}")
        response.raise_for_status()
        return response, asin
    except requests.HTTPError as errh:
        print(f"HTTP Error: {errh}")
        logging.warning(f"HTTP Error for {asin}")
    except requests.ConnectionError as errc:
        print(f"Connection Error: {errc}")
        logging.warning(f"Connection Error for {asin}")
    except requests.Timeout as errt:
        print(f"Timeout Error: {errt}")
        logging.warning(f"Timeout Error for {asin}")
    except requests.RequestException:
        logging.warning(f"HTTP Error for {asin}")
   

# Check stock status
def check_stock_status(html_content):
    soup = BeautifulSoup(html_content, 'lxml')

    # Check if the out of stock div is present
    out_of_stock_div = soup.find('div', id='outOfStock')

    # If the out of stock div is present, the item is out of stock
    if out_of_stock_div:
        print('Item is out of stock')
        return True
    else:
        # Check if the "Currently unavailable" text is present in the HTML
        unavailable_text = soup.find('span', class_='a-declarative', text='Currently unavailable.')
        if unavailable_text:
            print('Item is out of stock')
            return True
        else:
            print('Item is in stock')
            return False


def extract_data(response: tuple):
    soup = BeautifulSoup(response[0].text, 'lxml')
    asin = response[1]
    aplus_module_div = soup.find('div', class_='aplus-module-wrapper')

    
    logging.info(f"Item {asin} is in stock")

    try:
        title = soup.select_one("span#productTitle")
        if title is None:
            raise AttributeError
        price = soup.select_one("span.a-price span")
        if price is None:
            raise AttributeError
        feature_bullets = soup.select_one("div#feature-bullets")
        if feature_bullets is None:
            raise AttributeError
        
        # Initialise outside the if block
        h3_text = None
        p_text = None

        if isinstance(aplus_module_div, bs4.Tag):
            # Navigate to the h3 and p element
            h3_element = aplus_module_div.find('h3')
            p_elements = aplus_module_div.find_all('p')
            
            # Extract the text content from h3 and all p elements within the div
            h3_text = h3_element.text.strip() if h3_element else None
            p_text = [p.text.strip() for p in p_elements] if p_elements else None
        
        item = (
            asin,
            title.text.strip(),
            price.text.strip(),
            feature_bullets.text.strip(),
            h3_text,
            p_text,
        ),
        logging.info(f'scraped item successfully {item}')
        # print item to console
        print(f"All items: {item}")
        # print only the first item in the tuple
        print(f"First item: {item[0]}")
        return item[0]
    except AttributeError:
        logging.info(f"No Matching Selectors found for {asin}")
        item = (asin, "no data", "no data", "no data" , "no data")
        # print item to console
        print(f"All items: {item}")
        # print only the first item in the tuple
        print(f"First item: {item[0]}")
        return item[0]

# CSV Writing: When writing to a CSV file, you might want to consider using csv.DictWriter instead of csv.writer if your data can be represented as dictionaries. This can make your code more readable and maintainable.
def save_to_csv(results: list):
    with open('intermediate/results8.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['asin', 'title', 'price', 'feature_bullets', 'h3_text', 'p_text']
        csv_writer = csv.DictWriter(f, fieldnames=fieldnames)
        csv_writer.writeheader()

        for line in results:
            if isinstance(line[0], tuple):  # Handle the case where line[0] is a tuple
                for item in line:
                    csv_writer.writerow({'asin': item[0], 'title': item[1], 'price': item[2], 'feature_bullets': item[3], 'h3_text': item[4][0] if item[4] else None, 'p_text': item[5][0] if item[5] else None})
            else:
                # Handle the case where line[0] is not a tuple
                csv_writer.writerow({'asin': line[0], 'title': line[1], 'price': line[2], 'feature_bullets': line[3], 'h3_text': line[4][0] if line[4] else None, 'p_text': line[5][0] if line[5] else None})

    logging.info("saved file sucessfully")


def main():
    logging.basicConfig(filename='amzscraper.log', format='%(asctime)s %(message)s', level=logging.INFO)
    logging.info(f"---starting new---")

    results = []
    client = http_client()
    baseurl = "https://www.amazon.co.uk"
    asins = open_asins_from_file('intermediate/asins.csv')
    for asin in asins:
        html = make_request(client, baseurl, asin)
        if html is None:
            logging.info("passing due to make_request error")
        else:
            results.append(extract_data(html))
        
        # Add a delay of, for example, 3 seconds between requests
        time.sleep(3)

    save_to_csv(results)
    logging.info(f"---finished---")

if __name__ == '__main__':
    main()
