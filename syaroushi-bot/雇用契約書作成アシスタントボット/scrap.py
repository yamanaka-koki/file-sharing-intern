from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import re

import pandas as pd
import json
"""
section 1 : extract all urls. Each url corresponds to single inquiry. There are total of 100 inquiries. 
Inquiry is list up based on the keyword "雇用契約書" 
"""

# get entire html code from single url 
def get_html_code(url):
    req = Request(url)
    html_page = urlopen(req)
    soup = BeautifulSoup(html_page, "lxml")

    return soup 

# get all urls from the q&a list section page
def get_all_url(url): 

    # get all links in the page
    req = Request(url)
    html_page = urlopen(req)
    soup = BeautifulSoup(html_page, "lxml")

    links = []
    for link in soup.findAll('a'):
        links.append(link.get('href'))

    return links 

# 
def extract_qa_links(all_links): 
    
    import re 
    pattern = r"https://jinjibu\.jp/qa"

    # Initialize an empty list to store the matching URLs
    matching_urls = []

    # Iterate through the list of URLs and check if each one matches the pattern
    for url in all_links:
        if re.search(pattern, url):
            matching_urls.append(url)

    matches = []
    # Print the matching URLs
    for match in matching_urls:
        matches.append(match)

    # remove duplicates 
    matches = list(set(matches))
    return matches 

# returns all urls from 1 to 100, each corresponds to a single inquiry. Note: the order of q&a listing is different than the website. 
# format is in 2d list. each 1d correspond to 1-10 q&a
def flip_chrome_pages(base_url,search_query,filter_value):

    result_urls = []
    # Loop from 1 to 10 to generate and print the URLs
    for i in range(1, 11):
        # gets the single page url 
        url = f"{base_url}{i}/?kwd={search_query}&filter={filter_value}"

        # open single page 
        result  = get_all_url(url)

        # for each page, extract link that is q&a 
        result = extract_qa_links(result)

        result_urls.append(result)
    return result_urls

"""
section 2: get questions answer text data
"""

# extract date and id from each answer 
def extract_date_id(questions_text): 
    # Define a regex pattern to match the date format
    date_pattern = r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2})'
    id_pattern =  r'ID：(\w+-\d+)'

    # Use re.search to find the date in the text
    match_date = re.search(date_pattern, questions_text)
    match_id = re.search(id_pattern, questions_text)

    # Extract the matched date if found
    date = match_date.group(1)
    id = match_id.group(1)

    return date, id

# returns <string> title,question,answers for each page  
def get_title_questions_answers(singleqa_url): 

    # get whole html code with soup object
    soup_object  = get_html_code(singleqa_url)

    # @ get title 
    title_element = soup_object.find("h1")
    title = title_element.get_text(strip=True)

    # @ get question section and extract the text string 
    div = soup_object.find("section", {"class": "questionbox"}).text.strip()
    index = div.find("投稿日") # find the index for 投稿日
    question = div[:index]  # Slice the string up to the index
    question = question.replace(" ","")
    question = question.replace("\n","")
     
    # @ get answers
    answerbox_sections = soup_object.find_all("section",class_='answerbox')
    answers_list = []
    for section in answerbox_sections:
        # Extract the text within the <section>
        text = section.get_text(separator=' ')
        
        # remove spaces, newline,\r
        text = text.replace(" ","")
        text = text.replace("\n","")
        text = text.replace("\r","")

        # add to list
        answers_list.append(text)

    return title,question,answers_list # returns answers_list: a list of answers

def output_csv(): 
    # get all urls related to a keyword. e.g. 雇用契約書

    # setup a base url to return all urls 
    base_url = "https://jinjibu.jp/search/list/"
    search_query = "%E9%9B%87%E7%94%A8%E5%A5%91%E7%B4%84%E6%9B%B8"  # in actual, it looks like this /10/?kwd=雇用契約書&filter=9
    filter_value = "9"

    # returns all urls related 雇用契約書
    data = [] # to store all data in lists of dictionaries 
    data_answers = [] 
    result_urls = flip_chrome_pages(base_url,search_query,filter_value)

    for i in range(len(result_urls)): # iterate 1 to 10 listing q&a page 
        for j in range(len(result_urls[i])): # iterate each q&a from 1 to 10 

            # insert title,question,url. Note: we exclude the answers from data list 
            data.append({"Title":get_title_questions_answers(result_urls[i][j])[0], "Question": get_title_questions_answers(result_urls[i][j])[1], 
                "URL":result_urls[i][j]})
            # insert 
            data_answers.append({"Answers":get_title_questions_answers(result_urls[i][j])[2],"URL":result_urls[i][j]})

        print("completed batch"+str(i))
         
    # write data into csv file 
    df = pd.DataFrame(data)
    csv_path = 'data.csv'
    df.to_csv(csv_path, index=False)
    
    # write data - answers into json file 
    with open("answers.json", "w", encoding="utf-8") as json_file:
        json.dump(data_answers, json_file, indent=4, ensure_ascii=False)


          

"""
section 3: clean the missing part of data
"""

# Split the text based on the "投稿日：" pattern and get the part after it
def cut_responsetext(text):
    parts = text.split("投稿日：")
    desired_part = parts[0].strip()
    return desired_part

# writes another json file. purpose is to remove answer's following user response 
# removal part e.g 相談者より
#的確なご回答に感謝申し上げます。
#ご回答を参考に準備を進めたいと思います。

def clean_answer_data():

    import json

    # Read the data from the JSON file
    with open('answers.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    new_data = []
    # Iterate through the data and extract each answer
    for entry in data:
        answers = entry["Answers"]
        urls = entry["URL"]
        page_data = []
        for i, answer in enumerate(answers, start=1): # iterate each page's answers 
            
            # print(f"Answer {i}:\n")
            page_data.append(cut_responsetext(answer))
        new_data.append({"Answers":page_data,"URL":urls})
    
    # write data - answers into json file 
    with open("answers_refined.json", "w", encoding="utf-8") as json_file:
        json.dump(new_data, json_file, indent=4, ensure_ascii=False)

clean_answer_data()

        

if __name__ == "__main__":

    # single page scrapping 
    test_url = 'https://jinjibu.jp/qa/detl/107990/1/'
    test2 = 'https://jinjibu.jp/qa/detl/64676/1/'

    
    output_csv()
# python scrap.py