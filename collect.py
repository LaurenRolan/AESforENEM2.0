from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from tqdm.auto import tqdm

import codecs
import pandas as pd
import re
import sys
import os

def hide_ads(driver : webdriver.Chrome):
    all_iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if len(all_iframes) > 0:
        print("Ad Found\n")
        driver.execute_script("""
            var elems = document.getElementsByTagName("iframe"); 
            for(var i = 0, max = elems.length; i < max; i++)
                {
                    elems[i].hidden=true;
                }
                            """)
        print('Total Ads: ' + str(len(all_iframes)))
    else:
        print('No frames found')

def scroll_to_end(driver : webdriver.Chrome):
    # Go to the end of the page and keep clicking on the "Ver mais" button
    button_more = True
    sleep(10)
    while button_more:
        more_button = driver.find_element(By.ID, 'load-more-btn')
        driver.execute_script("arguments[0].scrollIntoView();", more_button)
        sleep(2)
        try:
            more_button.click()
            sleep(1)
        except:
            button_more = False
    sleep(2)

def collect_all_theme_links(driver : webdriver.Chrome):
    # Get all the links and themes from the table and save them
    theme_table = driver.find_element(By.ID, 'table-temas')

    table_rows = theme_table.find_elements(By.TAG_NAME, 'tr')[1:]

    themes = []
    progress = range(len(table_rows))
    for row, _ in zip(table_rows, tqdm(progress)):
        a_element = row.find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'a')
        link = a_element.get_property('href')
        theme = a_element.text
        date = row.find_elements(By.TAG_NAME, 'td')[1].text
        month = date.split('/')[0]
        year = date.split('/')[1]
        date = date.replace('/', '-')
        themes.append([theme, link, month, year, date])
        
    df = pd.DataFrame(themes, columns=['Theme', 'Link', 'Month', 'Year', 'Date'])
    df.to_csv('data/links.csv', index=False)

    return df

def get_essays_links_by_theme(driver : webdriver.Chrome, theme_link : str, date: str):
    driver.get(theme_link)
    theme_paragraph = driver.find_element(By.CLASS_NAME, 'texto-conteudo').find_element(By.TAG_NAME, 'p').text
    table_corrected = driver.find_element(By.ID, 'redacoes_corrigidas')
    essays_corrected = table_corrected.find_elements(By.TAG_NAME, 'tr')[1:]
    essays_links = []
    progress = range(len(essays_corrected))
    for essay, n, _ in zip(essays_corrected, progress, tqdm(progress)):
        a_element = essay.find_elements(By.TAG_NAME, 'td')[0].find_element(By.TAG_NAME, 'a')
        link = a_element.get_property('href')
        essays_links.append([theme_paragraph, n, link, date])

    df_theme = pd.DataFrame(essays_links, columns=['Proposition', 'Id', 'Link', 'Date'])
    df_theme.to_csv(f'data/{date}.csv', index=False)
    
    return df_theme

def get_essays_by_link(driver : webdriver.Chrome, links_file : str):
    df_links = pd.read_csv(links_file, index_col=None)
    progress = range(len(df_links))
    for link, id, date, _ in zip(df_links['Link'], df_links['Id'], df_links['Date'], tqdm(progress)):
        # Check if the essays were already collected
        output_dir = Path(f'data/essays/{date}')
        
        n_files = 0
        if output_dir.exists():
            n_files = len(os.listdir(output_dir))
        if n_files == len(df_links):
            continue
        if n_files >= id + 1:
            continue
        
        driver.get(link)
        sleep(1)
        paragraphs = driver.find_element(By.CLASS_NAME, 'area-redacao-corrigida').find_elements(By.TAG_NAME, 'p')
        essay_raw = ""
        for p in paragraphs:
            essay_raw += p.text
        essay_clean = re.sub("\(.*?\)", "", essay_raw.text)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        f = codecs.open(output_dir / f"{id}.txt", "w", "utf-8")
        f.write(essay_clean)
        f.close()

if __name__ == '__main__':
    args = sys.argv
    if len(args) == 1:
        print("Usage: \n   python collect.py <args>\n\nArgs:\n   links: gets all theme and essay links\n   essays: saves all essays to txt files")
        exit(1)
    
    args = args[1:]
    
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options, keep_alive=True)
    
    # Set window on my left screen and maximize
    driver.set_window_position(-1000, 0)
    driver.maximize_window()
    
    driver.get('https://vestibular.brasilescola.uol.com.br/banco-de-redacoes')

    if "links" in args:
        scroll_to_end(driver)
        df_themes = collect_all_theme_links(driver)
        progress = range(len(df_themes))
        for link, date, _ in zip(df_themes['Link'], df_themes['Date'], tqdm(progress)):
            _ = get_essays_links_by_theme(driver, link, date)
    
    if "essays" in args:
        essay_links = list(os.walk("data/"))[0][2]
        essay_links.remove("links.csv")
        progress = range(len(essay_links))
        for link, _ in zip(essay_links, tqdm(progress)):
            path = f"data/{link}"
            get_essays_by_link(driver, path)
    