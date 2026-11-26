import argparse
from dotenv import load_dotenv
import os
import json
from sparql_helpers import get_entity, extract_values
import time
from urllib.error import HTTPError
from SPARQLWrapper import SPARQLWrapper, JSON

def main():
    #parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("language")
    parser.add_argument("language_abrv")
    parser.add_argument("--big", action="store_true")
    args = parser.parse_args()
    language_abrv = args.language_abrv
    language= args.language
    big = args.big

    #get env variables
    load_dotenv()
    user_email = os.environ.get('SPAREMAIL')
    print(f"user email {user_email}")

    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.addCustomHttpHeader(
        "User-Agent",
        f"MyWikidataTranslator/1.0 ({user_email})"
    )

    if big:
        folder = "./BEAR-big/english"
        language_folder =  f"./BEAR-big/{language}"
    else:
        folder = "./BEAR/english"
        language_folder =  f"./BEAR/{language}"

    print(f"translating jsonl files in {folder} to {language_abrv}")

    files = os.listdir(folder)

    print(f"translating {len(files)} files")

    # Translation results, reports total rows and translated rows
    results = {}

    #total skipped rows counter
    skipped = 0
    for file_name in files:
        #check file extension
        extension = file_name.split(sep='.')[-1]
        if (extension != "jsonl"):
            print(f"{file_name} is not jsonl skipping translation")
            continue

        #setup maps 
        data =[]
        lines = []

        #open file and collect ids 
        with open(folder + "/" + file_name, "r") as file:
            for i, line in enumerate(file):
                obj = json.loads(line)
                lines.append(obj)
                sub_id = obj['sub_id']
                obj_id = obj['obj_id']
                data.append(sub_id)
                data.append(obj_id)
            data_size = len(data) 
            batch_size = 300
            batches = [data[i:i + batch_size] for i in range(0, data_size, batch_size)]


        translations = []
        #make translation call to wiki data 
        for data in batches:
            batch_translations = None
            count = 0
            while batch_translations == None:
                count+=1
                try:
                    batch_translations = get_entity(data, language_abrv, sparql_endpoint=sparql)
                except HTTPError as exc:
                    if exc.code != 429:
                        print(f"exeption {exc}")
                    print(f"wiki data call failed {count} times waiting 60 seconds")
                    time.sleep(70)
                except Exception as exc:
                    print(f"translation for {file_name} failed due to {exc}")
            translations.extend(batch_translations)

        translation_map = {}
        for result in translations:
            id, label, alias = extract_values(result)
            if label:
                translation_map[id] = (label, alias)

        #copy file into new folder and replace labels and alias with translations 
        translated_lines = []
        for line in lines:
            sub_id = line.get('sub_id')
            ob_id = line.get('obj_id')
            if (sub_id not in translation_map or ob_id not in translation_map):
                skipped += 1
            else: 
                line['sub_label'] = translation_map.get(line['sub_id'])[0]
                if(translation_map.get(line['sub_id'])[1]):
                    line['sub_aliases'] = translation_map.get(line['sub_id'])[1]
            
                line['obj_label'] = translation_map[line['obj_id']][0]
                if(translation_map[line['obj_id']][1]):
                    line['obj_aliases'] = translation_map[line['obj_id']][1]
                translated_lines.append(line)
        
        os.makedirs(language_folder, exist_ok=True) 
        with open(language_folder + "/" + file_name, "w", encoding='utf-8') as f:
            # TODO go into BEAR and translate this 
            for record in translated_lines:
                f.write(json.dumps(record) + '\n')
                    
        results[file_name.split('.')[0]] = {'total': len(lines), 'translated': len(translated_lines)}

    with open(language_folder + "/translations_info.json", "w", encoding='utf-8') as f:
        f.write(json.dumps(results))

if __name__ == "__main__":
    main()  





            