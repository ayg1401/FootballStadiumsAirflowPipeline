import json
import pandas as pd

import os
import sys
import logging



no_image="https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg"
def get_wikipedia_page(url):
    import requests
    print("Getting wiki page", url)
    try:
        response=requests.get(url,timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"An error incident: {e}")

def get_wikipedia_data(html):
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,'html.parser')
    table=soup.find_all("table",{"class":"wikitable sortable sticky-header"})[0]
    # wikitable sortable sticky-header jquery-tablesorter
    table_rows=table.find_all('tr')

    return table_rows

def extract_wikipedia_data(**kwargs):
    import pandas as pd
    url=kwargs['url']
    html=get_wikipedia_page(url)
    rows=get_wikipedia_data(html)

    # print("Num of ROWS97",rows)
    data=[]
    for i in range (1,len(rows)):
        tds=rows[i].find_all('td')
        values={
            'rank':i,
            'stadium':tds[0].text.replace("♦",""),
            'capacity':tds[1].text.split("[")[0].replace(",",""),
            'region':tds[2].text,
            'country':tds[3].text,
            'city':tds[4].text,
            'image':"https://"+tds[5].find('img').get('src').split('//')[1] if tds[5].find('img') else "NO_IMAGE" ,
            'home_team':tds[6].text
        }
        data.append(values)
    data_df=pd.DataFrame(data)

    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    print("CUrr File PATH:",(os.path.abspath(__file__)))
    print("Path TO THE op: ",os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
    data_df.to_csv(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/output.csv',index=False)
    json_rows=json.dumps(data)
    kwargs['ti'].xcom_push(key='rows',value=json_rows)
    return "ok"

def get_lat_long(country,city):
    from geopy.geocoders import Nominatim

    logger = logging.getLogger(__name__)
    logger.info("This is a log message")
    geolocator = Nominatim(user_agent="Locate Stadium")
    location = geolocator.geocode(f'{city},{country}')

    if location:
        return location.latitude,location.longitude

    return None

def transform_wikipedia_data(**kwargs):
    data=kwargs['ti'].xcom_pull(key='rows',task_ids='extract_data_from_wikipedia')
    print("data")
    logger = logging.getLogger(__name__)
    logger.info("This is a log message data: "+data)
    data=json.loads(data)
    stadium_df=pd.DataFrame(data)
    stadium_df['location']=stadium_df.apply(lambda x: get_lat_long(x["country"],x["stadium"]),axis=1)
    stadium_df['image']=stadium_df['image'].apply(lambda x: x if x not in ["NO_IMAGE",""," " ] else no_image)
    stadium_df['capacity']=stadium_df['capacity'].astype(int)
    duplicates=stadium_df[stadium_df.duplicated(['location'])]
    duplicates['location']=duplicates.apply(lambda x: get_lat_long(x["country"],x["city"]),axis=1)
    stadium_df.update(duplicates)


    kwargs['ti'].xcom_push(key='rows',value=stadium_df.to_json())

    return 'ok'

def write_wikipedia_data(**kwargs):
    from datetime import datetime
    data=kwargs['ti'].xcom_pull(key='rows',task_ids='transform_wikipedia_data')
    data=json.loads(data)
    data=pd.DataFrame(data)

    filename=('stadium_cleaned_'+str(datetime.now().date())
              +"_"+str(datetime.now().time()).replace(":","_")+".csv")
    sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    print("CUrr File PATH:",(os.path.abspath(__file__)))
    print("Path TO THE op: ",os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 

    data.to_csv(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/'+filename,index=False)
    # data.to_csv('abfs://footballdataeng@fballdeng.dfs.core.windows.net/data/'+filename,storage_options={
    #     'account_key':'74B0VZGM1ChL2wYSq+pQkeVF/MaZV6mqoCylVHzo6UGBgG5uvvpwxqcgFT5ZeYDqw9ienpXSqujB+ASts7+iag=='
    # },index=False)