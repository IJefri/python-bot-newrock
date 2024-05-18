import os
import telebot
import pandas as pd
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Retrieve bot token from environment variable
#BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Use the name of the environment variable

# Initialize bot
#bot = telebot.TeleBot(BOT_TOKEN)

BOT_TOKEN = "7176877320:AAGLMiDHUVe3J6fpqyzFrxBKLEYyJgLndkE"
def remove_files_in_dir(directory):
    files = os.listdir(directory)
    for file in files:
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Removed file: {file_path}")
            
# Initialize bot with the token
bot = telebot.TeleBot(BOT_TOKEN)
#-----------------------------------------------------------
def create_df(name):
    url = "https://www.newrock.com/ru/outlet/"
    all_urls = []
    page_number = 1
    prev_len = 0
    
    while True:
        page_url = f"{url}?page={page_number}"
        print(page_url)
        response = requests.get(page_url)
        if response.status_code != 200:
            print("Error: Failed to retrieve page")
            break  # Exit the loop if the page is not found or another error occurs
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("div", class_="product-description-short text-muted")
        for link in links:
            product_link = link.find("a", href=True)
            if product_link:
                all_urls.append(product_link["href"])
        print("Number of product links on this page:", len(all_urls))
        if len(all_urls) == prev_len:
            print("CREATE_DF: Exiting parsing loop")
            break  # Exit the loop if no new URLs are found
        prev_len = len(all_urls)
        page_number += 1
    
    df_urls = pd.DataFrame(all_urls, columns=['url'])
    df_valid_urls = df_urls[df_urls['url'] != '#'].drop_duplicates().reset_index(drop=True)
    print("Number of valid URLs:", df_valid_urls.nunique())
    df_valid_urls.to_csv(f'{name}.csv')
    print(f"DataFrame saved to {name}.csv")
    return pd.read_csv('all_info_newrock.csv')
#-----------------------------------------------------------
def get_product(row):
    print('getting product')
    url = row['url']
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    product_name = soup.find("h1", class_='h1 page-title')
    name = product_name.text.strip() if product_name  else None
    
    # Extract price
    price_tag = soup.find("span", class_="product-price")
    price = price_tag.text.strip() if price_tag else None

    # Extract sizes
    sizes_tags = soup.find_all("span", class_="radio-label")
    sizes = [size_tag.text.strip() for size_tag in sizes_tags]

    # Extract image URL if available
    image_div = soup.find("a", class_="js-easyzoom-trigger")
    images = image_div.get('href') if image_div else None
    
    return pd.Series({'url': url, 'price': price, 'sizes': sizes,'images': images, 'model':name})

def make_url(df):
    df_razmer = df[df['url'].str.contains('razmer')]
    for index, row in df_razmer.iterrows():
        url = row['url']  # Get the URL from the current row
        last_slash_index = url.rfind('/')
        hash_index = url.rfind('#')

        if last_slash_index != -1:
            if hash_index != -1 and hash_index > last_slash_index:
                new_url = url
            else:
                new_url = url[:last_slash_index]
            #print(new_url)
        else:
            print("No '/' character found in the URL")
    df_wo_razmer = df[~df['url'].str.contains('razmer')]
    df_with_razer = df[~df['url'].str.contains('razmer')]
    result = pd.concat([df_with_razer,df_wo_razmer])
    return result

#-----------------------------------------------------------
#chat_id = 758795444
#result_new = handle_new(chat_id)



#-----------------------------------------------------------
#bot.send_message(758795444, f'{result_new}')
#-----------------------------------------------------------
@bot.message_handler(commands=['sendmessage'])
def handle_send_message(message):
    chat_id = message.chat.id 

    for index, row in df_valid_urls.iterrows():
        image_url = row["images"]
        descriptions = row["sizes"]
        caption = ", ".join(map(str, descriptions))
        bot.send_photo(chat_id, image_url, caption=caption)
#-----------------------------------------------------------
@bot.message_handler(commands=['updateold'])
def hande_update(message):
    if type(message) == telebot.types.Message:
        chat_id = message.chat.id
    else:
        chat_id = message
        
    current_date_time = datetime.now()
    current_date = current_date_time.date()
    files = os.listdir('newrock_old')
    i = len(files)
    
    create_df(f'newrock_old/newrock_{current_date}_{i}')
    print(f'created newrock_{current_date}')
    # Get the current date and time
    
    print("Current date:", current_date)
    #bot.send_message(chat_id, f'created newrock_{current_date}')
#-----------------------------------------------------------
@bot.message_handler(commands=['id'])
def hande_id(message):
    chat_id = message.chat.id
    
    bot.send_message(chat_id, f"chat id: {chat_id}")


def handle_newnew(message):
    handle_new(message)
#-----------------------------------------------------------
@bot.message_handler(commands=['new'])
def handle_new(message):
    if type(message) == telebot.types.Message:
        chat_id = message.chat.id
    else:
        chat_id = message
        
    files = os.listdir('newrock_old')
    oldest_url_list = pd.DataFrame()

    print(f'--------READING+{len(files)}-------------------------------')
    for file in files:
        print(f'reading+{file}')
        df_file1 = pd.read_csv(f'newrock_old/{file}')
        oldest_url_list = pd.concat([oldest_url_list, df_file1])
    
    oldest_url_list = pd.DataFrame(oldest_url_list['url'].drop_duplicates())
    oldest_url_list = make_url(oldest_url_list)
    oldest_url_list['url'] = oldest_url_list['url'].str.replace('#', '')
    oldest_url_list.to_excel('url_list_test.xlsx')
    
    all_info_newrock = create_df('all_info_newrock') # df
    all_info_newrock = make_url(all_info_newrock)
    all_info_newrock['url'] = all_info_newrock['url'].str.replace('#', '')
    all_info_newrock.to_excel('all_info_newrock_test.xlsx')
    if oldest_url_list.empty:
        print('------------------------------------- NO NEW 0 -------------------------------')
    if not oldest_url_list.empty:
        new_urls_df = all_info_newrock[~all_info_newrock['url'].isin(oldest_url_list['url'])]
        new_urls_df = new_urls_df.drop(columns='Unnamed: 0').reset_index(drop=True)
        new_urls_df.to_excel('new_urls_df_test.xlsx')
        print(f'------------------------------------- NEW {new_urls_df.shape[0]} -------------------------------')

        # all_info_newrock - свежие ссылки
        # url_list - все пред ссылки на ВСЕ товары
        # new_urls_df - сборка НОВЫХ ссылок на товары

        if not new_urls_df.empty:
            new_urls_df_parsed = new_urls_df.apply(get_product, axis=1) 
            new_urls_df_parsed = new_urls_df_parsed.drop_duplicates(subset=['model'])
            #new_urls_df_parsed = new_urls_df_parsed.drop_duplicates()
            new_urls_df_parsed.to_excel('new_urls_df_parsed.xlsx')

            #url_list = url_list.apply(get_product, axis=1)
            #new_urls_df_parsed = new_urls_df_parsed[~new_urls_df_parsed['model'].isin(url_list['model'])]

            for index, row in new_urls_df_parsed.iterrows():
                print(row)
                product_url = row['url']
                image_url = row["images"]
                descriptions = row["sizes"]
                caption = ", ".join(map(str, descriptions)) + product_url
                print('------------------- SENDING PRODUCT ---------------------')
                bot.send_photo(430697715, image_url, caption=caption)
                bot.send_photo(758795444, image_url, caption=caption)
            print('saving new df')

            i = len(files)
            current_date_time = datetime.now()
            current_date = current_date_time.date()
            new_urls_df.to_csv(f'newrock_old/newrock_new_{current_date}_{i}.csv')
            
            #handle_newnew(message)
        #else:  bot.send_message(chat_id, f"chat id failed: {chat_id}")
#-----------------------------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(handle_new, 'interval', minutes=5, args=[430697715])
#scheduler.add_job(handle_new, 'interval', minutes=5, args=[758795444]) 
scheduler.start()

bot.polling()
